import gzip
import json
from typing import Any

import httpx

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.shopify.batch_processes import ShopifyBatchProcessORM
from wh_product_manager.db.models.shopify.object_assignments import (
    ShopifyObjectAssignmentORM,
)
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

allowed_operations = ("create_products",)


class ShopifyBatchUpdate:
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

    async def refresh(self) -> dict[str, Any]:
        self.logger.info("Refreshing Shopify batch processes")

        batches = await self.shopify_batch_processes_repo.get()

        batches = {
            batch.id: batch
            for batch in batches.values()
            if batch.shopify_id
            and batch.status not in ("COMPLETED", "FAILED", "finished")
        }

        self.logger.info(f"Found {len(batches)} batch processes to refresh")

        for batch in batches.values():
            self.logger.info(f"Refreshing batch process with id={batch.id}")

            store = await self.shopify_store_authentication_repo.get_store_by_id(
                batch.store_id
            )

            try:
                # Step 1: Fetch the status of the batch process from Shopify
                status_result = await self._fetch_batch_status(
                    store.store_id,
                    batch.shopify_id,  # type: ignore
                )

                # Step 2: Retrieve batch results if URL in results
                batch_result = None
                if status_result.get("url"):
                    batch_result = await self._download_batch_results(
                        status_result.get("url")  # type: ignore
                    )

                # Step 3: Update the batch process status in the database
                batch.status = status_result.get("status", "unknown")
                batch.objects_processed = status_result.get("objectCount", 0)
                batch.result = batch_result
                await self.shopify_batch_processes_repo.update_batch_process(batch)

                # Step 4: Process the batch results if available
                if batch_result and batch.status == "COMPLETED":
                    if batch.operation not in allowed_operations:
                        raise ValueError(
                            f"Unsupported operation '{batch.operation}' for batch process with id={batch.id}"
                        )

                    if batch.operation == "create_products":
                        await self._process_results__create_products(
                            batch, batch_result
                        )

            except Exception as e:
                self.logger.error(
                    f"Failed to refresh batch process with id={batch.id}: {e}"
                )
                continue

        return {
            "status": "success",
            "message": f"Refreshed {len(batches)} batch processes",
            "batches": [batch.id for batch in batches.values()],
        }

    async def _fetch_batch_status(
        self, store_id: str, shopify_id: str
    ) -> dict[str, Any]:
        mutation = f"""
            query {{
                node(id: "{shopify_id}") {{
                    ... on BulkOperation {{
                        id
                        status
                        errorCode
                        createdAt
                        completedAt
                        objectCount
                        fileSize
                        url
                    }}
                }}
            }}
        """

        result = await self.shopify_client.run(mutation, store_id)

        return result.get("data", {}).get("node", {})

    async def _download_batch_results(self, url: str) -> str:
        """Download bulk operation results and return JSONL content as text."""
        self.logger.debug("Downloading Shopify batch results")

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=60.0)

            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            content_encoding = response.headers.get("content-encoding", "").lower()

            is_gzip = (
                url.lower().endswith(".gz")
                or "gzip" in content_type
                or "gzip" in content_encoding
            )

            if is_gzip:
                try:
                    result_text = gzip.decompress(response.content).decode("utf-8")
                except OSError:
                    # Some responses are transparently decompressed by the HTTP client.
                    result_text = response.text
            else:
                result_text = response.text

            self.logger.info("Downloaded Shopify batch results successfully")

            return result_text

        except httpx.HTTPError as e:
            self.logger.error("Failed to download Shopify batch results:", e)
            raise

    async def _process_results__create_products(
        self, batch: ShopifyBatchProcessORM, batch_result: str
    ) -> dict[str, Any]:
        objects_to_publish: list[ShopifyObjectAssignmentORM] = []

        batch_variables: dict[str, Any] = batch.variables  # type: ignore

        batch_result_filtered: dict[int, Any] = {}
        batch_result_lines = batch_result.split("\n")
        for line in batch_result_lines:
            if line.strip():
                try:
                    result_data = json.loads(line)

                    linenumber = result_data.get("__lineNumber")

                    batch_result_filtered[int(linenumber)] = result_data.get("data", {})

                except json.JSONDecodeError as e:
                    self.logger.error(
                        f"Failed to decode JSON line in batch results for batch_id={batch.id}: {e}"
                    )

        for i in range(len(batch_variables)):
            this_batch_variables: dict[str, Any] = batch_variables.get(str(i), {})
            this_batch_result: dict[str, Any] = batch_result_filtered.get(i, {})

            print("\n\n")
            print(this_batch_variables)
            print("\n\n")
            print(this_batch_result)
            print("\n\n")

            if not this_batch_variables or not this_batch_result:
                self.logger.warning(
                    f"Missing variables or results for line {i} in batch_id={batch.id}"
                )
                continue

            product_id = this_batch_variables.get("product_id")
            variants_results = {
                item.get("sku"): item.get("id")
                for item in this_batch_result.get("productSet", {})
                .get("product", {})
                .get("variants", {})
                .get("nodes", [])
            }

            product_id_shopify = (
                this_batch_result.get("productSet", {}).get("product", {}).get("id")
            )
            variants: dict[str, dict[str, int | str | None]] = {
                sku: {
                    "variant_id": var_id,
                    "shopify_id": variants_results.get(sku, None),
                }
                for sku, var_id in this_batch_variables.get("variant_ids", {}).items()
            }

            if None in [
                variants_results.get(sku, None)
                for sku in this_batch_variables.get("variant_ids", {})
            ]:
                self.logger.warning(
                    f"Some variants were not created successfully for product_id={product_id} in batch_id={batch.id}"
                )

            product_assignment = ShopifyObjectAssignmentORM(
                store_id=batch.store_id,
                local_object_type="product",
                local_object_id=product_id,
                shopify_object_type="product",
                shopify_id=product_id_shopify,
                is_active=False,
            )

            product_assignment = (
                await self.shopify_object_assignments_repo.create_assignment(
                    product_assignment
                )
            )
            objects_to_publish.append(product_assignment)

            for variant in variants.values():
                variant_assignment = ShopifyObjectAssignmentORM(
                    store_id=batch.store_id,
                    local_object_type="variant",
                    local_object_id=variant.get("variant_id"),
                    shopify_object_type="product_variant",
                    shopify_id=variant.get("shopify_id"),
                    is_active=False,
                )

                variant_assignment = (
                    await self.shopify_object_assignments_repo.create_assignment(
                        variant_assignment
                    )
                )
                objects_to_publish.append(variant_assignment)

        batch.status = "finished"

        await self.shopify_batch_processes_repo.update_batch_process(batch)

        return {}
