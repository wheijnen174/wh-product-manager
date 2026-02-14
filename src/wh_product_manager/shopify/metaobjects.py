from asyncio import sleep
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.utils.data_loader import save_json


class MetaobjectService:
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
        query = self._query_get_definitions()

        cursor = None

        existing_definitions: dict[str, Any] = {}

        while True:
            variables: dict[str, Any] = {
                "cursor": cursor,
            }

            response = await self.shopify_client.query(query, variables)

            data = response.get("data", {}).get("metaobjectDefinitions", {})

            batch_data = data.get("edges", [])

            for item in batch_data:
                node = item.get("node", {})

                object_id = node.get("id")
                object_name = node.get("name")
                object_type = node.get("type")
                object_values: dict[str, Any] = {}

                for entry in node.get("metaobjects", {}).get("nodes", []):
                    entry_id = entry.get("id")
                    entry_handle = entry.get("handle")

                    object_values[entry_handle] = {
                        "id": entry_id,
                        "values": {
                            field.get("key"): field.get("value")
                            for field in entry.get("fields", [])
                        },
                    }

                existing_definitions[object_name] = {
                    "id": object_id,
                    "type": object_type,
                    "more_values": node["metaobjects"]["pageInfo"]["endCursor"]
                    if node["metaobjects"]["pageInfo"]["hasNextPage"]
                    else None,
                    "values": object_values,
                }

            if not data["pageInfo"]["hasNextPage"]:
                break

            cursor = data["pageInfo"]["endCursor"]

            await sleep(self.settings.SHOPIFY_API_BATCH_DELAY)  # Rate limiting delay

        have_large_objects = (
            True
            if len(
                [
                    x["more_values"]
                    for x in existing_definitions.values()
                    if x["more_values"] is not None
                ]
            )
            > 0
            else False
        )

        if have_large_objects:
            self.logger.warning(
                "One or more metaobject definitions have more values than the Shopify API batch limit. This may result in incomplete data being fetched. Consider implementing additional batching logic to fetch all values for these definitions."
            )

        save_json(
            "_debug_metaobject_definitions.json", existing_definitions, True, True
        )

        return dict(sorted(existing_definitions.items()))

    async def _get_values(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def _query_get_definitions(query_name: str | None = None) -> str:
        """
        GraphQL query for fetching metaobject definitions from Shopify

        Query args:
            cursor: Pagination cursor for batching through results

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($cursor: String) {{
                metaobjectDefinitions(first: 250, after: $cursor) {{
                    edges {{
                        node {{
                            id
                            type
                            name
                            metaobjects(first: 250) {{
                                nodes {{
                                    id
                                    handle
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

    def _query_get_values(self, query_name: str | None = None) -> str:
        """
        GraphQL query for fetching metaobject values from Shopify

        Query args:
            cursor: Pagination cursor for batching through results

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($cursor: String) {{
                metaobjectDefinitions(first: 250, after: $cursor) {{
                    edges {{
                        node {{
                            id
                            type
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
