from asyncio import sleep
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
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

    async def get_definitions(self, owner_type: str) -> dict[str, Any]:
        query = self._query_get_definitions()

        cursor = None

        existing_definitions: dict[str, Any] = {}

        while True:
            variables: dict[str, Any] = {
                "ownerType": owner_type,
                "cursor": cursor,
            }

            response = await self.shopify_client.query(query, variables)

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

            if not data["pageInfo"]["hasNextPage"]:
                break

            cursor = data["pageInfo"]["endCursor"]

            await sleep(self.settings.SHOPIFY_API_BATCH_DELAY)  # Rate limiting delay

        return dict(sorted(existing_definitions.items()))

    @staticmethod
    def _query_get_definitions(query_name: str | None = None) -> str:
        """
        GraphQL query for fetching metafield definitions from Shopify

        Query args:
            ownerType: The type of Shopify object the metafields are associated with (e.g., PRODUCT, VARIANT, etc.)
            cursor: Pagination cursor for batching through results

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($ownerType: MetafieldOwnerType!, $cursor: String) {{
                metafieldDefinitions(ownerType: $ownerType, first: 250, after: $cursor) {{
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
