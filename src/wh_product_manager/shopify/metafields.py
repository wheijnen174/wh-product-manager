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

    async def get_definitions(self) -> dict[str, Any]:

        return {}

        # query = self._query_get_definitions()

        # cursor = None

        # existing_definitions: dict[str, Any] = {}

        # while True:
        #     variables: dict[str, Any] = {
        #         "cursor": cursor,
        #     }

        #     response = await self.shopify_client.query(query, variables)

        #     data = response.get("data", {}).get("metafieldDefinitions", {})

        #     batch_data = data.get("edges", [])

        #     for item in batch_data:
        #         node = item.get("node", {})

        #         object_id = node.get("id")
        #         object_name = node.get("name")
        #         object_type = node.get("type")
        #         object_values: dict[str, list[str]] = {}

        #         for value in node.get("metafields", {}).get("nodes", []):
        #             for field in value.get("fields", []):
        #                 key = field.get("key")
        #                 value = field.get("value")

        #                 if key not in object_values:
        #                     object_values[key] = []

        #                 object_values[key].append(value)

        #         existing_definitions[object_name] = {
        #             "id": object_id,
        #             "type": object_type,
        #             "has_more_values": node["metafields"]["pageInfo"]["hasNextPage"],
        #             "values": object_values,
        #         }

        #     if not data["pageInfo"]["hasNextPage"]:
        #         break

        #     cursor = data["pageInfo"]["endCursor"]

        #     await sleep(self.settings.SHOPIFY_API_BATCH_DELAY)  # Rate limiting delay

        # save_json("_debug_metafield_definitions.json", existing_definitions, True, True)

        # return dict(sorted(existing_definitions.items()))

    async def _get_values(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def _query_get_definitions(query_name: str | None = None) -> str:
        """
        GraphQL query for fetching metafield definitions from Shopify

        Query args:
            cursor: Pagination cursor for batching through results

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($cursor: String) {{
                metafieldDefinitions(first: 250, after: $cursor) {{
                    edges {{
                        node {{
                            id
                            type
                            name
                            metafields(first: 250) {{
                                nodes {{
                                    fields {{
                                        key
                                        value
                                    }}
                                }}
                                pageInfo {{
                                    hasNextPage
                                    endCursor
                                }}
                            }}
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                }}
            }}
        """
