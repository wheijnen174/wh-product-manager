import json
from pathlib import Path
from typing import Any

import xmltodict

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.products import ProductsRepository
from wh_product_manager.db.repositories.shopify_batch_processes import (
    ShopifyBatchProcessesRepository,
)
from wh_product_manager.db.repositories.shopify_object_assignments import (
    ShopifyObjectAssignmentsRepository,
)
from wh_product_manager.db.repositories.shopify_store_authentication import (
    ShopifyStoreAuthenticationRepository,
)
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.utils.temp_file_service import TempFileService


class ShopifyBatchCreate:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
        temp_file_service: TempFileService,
        products_repo: ProductsRepository,
        shopify_object_assignments_repo: ShopifyObjectAssignmentsRepository,
        shopify_batch_processes_repo: ShopifyBatchProcessesRepository,
        shopify_store_authentication_repo: ShopifyStoreAuthenticationRepository,
    ):
        self.shopify_client = shopify_client
        self.logger = logger
        self.temp_file_service = temp_file_service

        self.products_repo = products_repo
        self.shopify_object_assignments_repo = shopify_object_assignments_repo
        self.shopify_batch_processes_repo = shopify_batch_processes_repo
        self.shopify_store_authentication_repo = shopify_store_authentication_repo

    async def execute(self) -> dict[str, Any]:
        self.logger.info("Executing Shopify batch processes")

        batches = await self.shopify_batch_processes_repo.get(status="pending")

        self.logger.info(f"Found {len(batches)} pending batches to execute")

        for batch in batches.values():
            self.logger.info(f"Executing batch process with id={batch.id}")

            if batch.query and batch.variables:
                store = await self.shopify_store_authentication_repo.get_store_by_id(
                    batch.store_id
                )

                try:
                    # Step 1: Write the variables to a temporary file
                    temp_file_path = await self._store_variables_file(
                        batch.variables  # type: ignore
                    )

                    # Step 2: Get the upload target from Shopify
                    upload_target = await self._get_upload_target(store.store_id)

                    # Step 3: Upload the temporary file to Shopify using the provided upload target
                    staged_upload = await self._upload_variables_file(
                        store.store_id, upload_target, temp_file_path
                    )

                    if staged_upload.get("status_code") != 201:
                        self.logger.error(
                            f"Failed to upload variables file for store_id={store.store_id}: {staged_upload}"
                        )
                        await self.shopify_batch_processes_repo.update_status(
                            batch.id, "upload_error"
                        )
                        continue

                    # Step 4: Execute the batch mutation on Shopify using the staged upload path
                    execution_result = await self._execute_batch_mutation(
                        store.store_id,
                        batch.query,
                        staged_upload.get("xml", {})
                        .get("PostResponse", {})
                        .get("Key", ""),
                    )

                    # Step 5: Update the batch process status to "executed"
                    batch.status = execution_result.get("bulkOperation", {}).get(
                        "status", "execution_error"
                    )
                    batch.shopify_id = execution_result.get("bulkOperation", {}).get(
                        "id", ""
                    )
                    await self.shopify_batch_processes_repo.update_batch_process(batch)

                except Exception as e:
                    self.logger.error(
                        f"Failed to get upload target for store_id={store.store_id}: {e}"
                    )
                    await self.shopify_batch_processes_repo.update_status(
                        batch.id, "internal_error"
                    )
                    continue

                # Step 5: Clean up the temporary file
                if temp_file_path.exists():
                    temp_file_path.unlink()
                    self.logger.info(f"Temporary file deleted: {temp_file_path}")

        return {
            "status": "success",
            "message": f"Executed {len(batches)} pending batches",
            "batches": [batch.id for batch in batches.values()],
        }

    async def _get_upload_target(self, store_id: str) -> dict[str, Any]:
        mutation = """
            mutation {
                stagedUploadsCreate(input:[{
                    resource: BULK_MUTATION_VARIABLES,
                    filename: "bulk_op_vars",
                    mimeType: "text/jsonl",
                    httpMethod: POST
                }]){
                userErrors{
                    field,
                    message
                },
                stagedTargets{
                    url,
                    resourceUrl,
                    parameters {
                        name,
                        value
                    }
                }
                }
            }
        """

        result = await self.shopify_client.run(mutation, store_id)

        return (
            result.get("data", {})
            .get("stagedUploadsCreate", {})
            .get("stagedTargets", [])[0]
        )

    async def _store_variables_file(self, variables: dict[Any, Any]) -> Path:
        """
        Store the given variables in a temporary file and return the file path.

        Args:
            variables: The variables to store in the temporary file.

        Returns:
            The path to the temporary file.
        """
        temp_file_path = self.temp_file_service.make_temp_file_path(
            prefix="whpm-", suffix=".jsonl"
        )

        variables_jsonl = "\n".join(
            [json.dumps(item["variables"]) for item in variables.values()]
        )

        with temp_file_path.open("w", encoding="utf-8") as temp_file:
            temp_file.write(variables_jsonl)

        return temp_file_path

    async def _upload_variables_file(
        self, store_id: str, upload_target: dict[str, Any], file_path: Path
    ) -> dict[str, Any]:
        """
        Upload the given variables file to Shopify using the provided upload target.

        Args:
            store_id: The Shopify store ID.
            upload_target: The upload target information from Shopify.
            file_path: The path to the temporary variables file.

        Returns:
            A dictionary containing the status and message of the upload operation.
        """
        form_variables = {
            param["name"]: param["value"] for param in upload_target["parameters"]
        }
        endpoint = upload_target["url"]

        result = await self.shopify_client.post(
            endpoint=endpoint,
            form_variables=form_variables,
            file_path=file_path,
            file_field_name="file",
            file_content_type="text/jsonl",
            store_id=store_id,
        )

        if isinstance(result.get("text", ""), str) and result.get("text", "").strip():
            try:
                result["xml"] = xmltodict.parse(result.get("text", ""))
            except Exception as e:
                self.logger.warning(
                    "Failed to parse staged upload XML response for store_id=%s: %s",
                    store_id,
                    e,
                )

        return result

    async def _execute_batch_mutation(
        self, store_id: str, mutation: str, staged_upload_path: str
    ) -> dict[str, Any]:
        """
        Execute the given batch mutation on Shopify.

        Args:
            store_id: The Shopify store ID.
            mutation: The batch mutation to execute.
            staged_upload_path: The path to the staged upload file.

        Returns:
            A dictionary containing the status and message of the execution operation.
        """

        batch_mutation = f"""
            mutation {{
                bulkOperationRunMutation(
                    mutation: "{mutation}",
                    stagedUploadPath: "{staged_upload_path}"
                ) {{
                    bulkOperation {{
                        id
                        url
                        status
                    }}
                    userErrors {{
                        message
                        field
                    }}
                }}
            }}
        """

        result = await self.shopify_client.run(batch_mutation, store_id)

        return result.get("data", {}).get("bulkOperationRunMutation", {})
