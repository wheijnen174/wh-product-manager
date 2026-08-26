import json
from asyncio import sleep
from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.settings import Settings
from wh_product_manager.shopify.client import ShopifyGraphQLClient


class MetafieldService:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
    ):
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger

    async def get_definitions(
        self, owner_type: str, namespace: str | None = None
    ) -> dict[str, Any]:
        self.logger.info(
            f"Starting metafield definitions fetch: owner_type={owner_type}, namespace={namespace}"
        )
        # await self.delete_all_metafields()
        # raise

        query = self._query_get_definitions()

        cursor = None

        existing_definitions: dict[str, Any] = {}

        while True:
            variables: dict[str, Any] = {
                "namespace": namespace,
                "ownerType": owner_type,
                "cursor": cursor,
            }

            response = await self.shopify_client.run(query, variables)

            data = response.get("data", {}).get("metafieldDefinitions", {})

            batch_data = data.get("edges", [])

            for item in batch_data:
                node = item.get("node", {})

                object_id = node.get("id")
                object_namespace = node.get("namespace")
                object_key = node.get("key")
                object_name = node.get("name")

                existing_definitions[object_name] = {
                    "id": object_id,
                    "namespace": object_namespace,
                    "key": object_key,
                }

            self.logger.debug(
                f"Fetched metafield definitions batch: batch_size={len(batch_data)}, accumulated={len(existing_definitions)}"
            )

            if not data["pageInfo"]["hasNextPage"]:
                break

            cursor = data["pageInfo"]["endCursor"]

            await sleep(self.settings.SHOPIFY_API_BATCH_DELAY)  # Rate limiting delay

        self.logger.info(
            f"Finished metafield definitions fetch: total={len(existing_definitions)}"
        )
        return dict(sorted(existing_definitions.items()))

    async def create_definition(
        self,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        self.logger.info("Starting metafield definition creation")

        mutation = self._mutation_create_definition()

        response = await self.shopify_client.run(mutation, variables)

        data = (
            response.get("data", {})
            .get("metafieldDefinitionCreate", {})
            .get("createdDefinition", {})
        )

        if not data:
            errors = (
                response.get("data", {})
                .get("metafieldDefinitionCreate", {})
                .get("userErrors", [])
            )
            self.logger.error(f"Failed to create metafield definition: {errors}")
            raise Exception(f"Metafield definition creation failed: {errors}")

        object_id = data.get("id")
        object_namespace = data.get("namespace")
        object_key = data.get("key")

        if not object_id or not object_namespace or not object_key:
            raise Exception(
                f"Metafield definition creation succeeded, but missing fields ('id', 'namespace', or 'key') in response: {response}"
            )

        self.logger.debug(
            f"Created metafield definition: id={object_id}, namespace={object_namespace}, key={object_key}"
        )

        return {
            "id": object_id,
            "namespace": object_namespace,
            "key": object_key,
        }

    @staticmethod
    def _query_get_definitions(query_name: str | None = None) -> str:
        """
        GraphQL query for fetching metafield definitions from Shopify

        Query args:
            namespace: Optional namespace to filter metafield definitions
            ownerType: The type of Shopify object the metafields are associated with (e.g., PRODUCT, VARIANT, etc.)
            cursor: Pagination cursor for batching through results

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($namespace: String, $ownerType: MetafieldOwnerType!, $cursor: String) {{
                metafieldDefinitions(namespace: $namespace, ownerType: $ownerType, first: 250, after: $cursor) {{
                    edges {{
                        node {{
                            id
                            namespace
                          	key
                          	name
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                }}
            }}
        """

    @staticmethod
    def _mutation_create_definition(query_name: str | None = None) -> str:
        """
        GraphQL mutation for creating metafield definitions in Shopify

        Mutation args:
            definition: The input object containing the details of the metafield definition to be created. Mandatory fields include:
                - namespace: The namespace for the metafield definition
                - key: The key for the metafield definition
                - name: The name for the metafield definition
                - ownerType: The type of Shopify object the metafield will be associated with (e.g., PRODUCT, VARIANT, etc.)
                - type: The data type of the metafield

        Args:
            query_name: Optional name for the mutation (for batching/debugging)
        Returns:
            str: GraphQL mutation string
        """

        return f"""
            mutation {query_name if query_name else ""}($definition: MetafieldDefinitionInput!) {{
                metafieldDefinitionCreate(definition: $definition) {{
                    createdDefinition {{
                        id
                        namespace
                        key
                    }}
                    userErrors {{
                        field
                        message
                    }}
                }}
            }}
        """

    async def delete_all_metafields(self) -> None:
        query_fetch = """
            query {
                metafieldDefinitions(first: 250, ownerType: PRODUCT, namespace: "product") {
                    nodes {
                        id
                        name
                    }
                    pageInfo {
                        hasNextPage
                    }
                }
            }
        """

        response_fetch = await self.shopify_client.run(
            query_fetch, enable_timeout=False
        )

        data = (
            response_fetch.get("data", {})
            .get("metafieldDefinitions", {})
            .get("nodes", [])
        )

        metafield_ids = [item["id"] for item in data]

        mutation_delete = """
            mutation {
        """

        for i, metafield_id in enumerate(metafield_ids):
            mutation_delete += f"""
                delete_metafield_{i + 1}: metafieldDefinitionDelete(deleteAllAssociatedMetafields: true, id: "{metafield_id}") {{
                    userErrors {{
                        field
                        message
                    }}
                }}
            """

        mutation_delete += """
            }
        """

        response_delete = await self.shopify_client.run(
            mutation_delete, enable_timeout=False
        )

        print(json.dumps(response_delete, indent=2))
        raise
