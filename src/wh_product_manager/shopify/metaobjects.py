from asyncio import sleep
from typing import Any

from slugify import slugify

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient


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
                    "more_values": node["metaobjects"]["pageInfo"]["hasNextPage"],
                    "values": object_values,
                }

            if not data["pageInfo"]["hasNextPage"]:
                break

            cursor = data["pageInfo"]["endCursor"]

            await sleep(self.settings.SHOPIFY_API_BATCH_DELAY)  # Rate limiting delay

        have_large_objects = True in [
            defn["more_values"] for defn in existing_definitions.values()
        ]

        if have_large_objects:
            self.logger.info(
                "Retrieving additional data for large metaobjects with more than 250 entries."
            )
            existing_definitions = await self._get_extra_values(existing_definitions)

        existing_definitions = {
            k: {sub_k: sub_v for sub_k, sub_v in v.items() if sub_k != "more_values"}
            for k, v in existing_definitions.items()
        }

        return dict(sorted(existing_definitions.items()))

    async def create_definition(
        self, name: str, details: dict[str, Any]
    ) -> dict[str, Any]:

        definition_name = details["namespace"] + " - " + name
        definition_key = (
            slugify(details["namespace"], separator="_").lower() + "-" + details["key"]
        )

        mutation = self._query_create_definition()

        variables: dict[str, Any] = {
            "definition": {
                "name": definition_name,
                "type": definition_key,
                "displayNameKey": details["key"],
                "fieldDefinitions": [
                    {
                        "name": name,
                        "key": details["key"],
                        "type": "single_line_text_field",
                        "required": True,
                        "capabilities": {"adminFilterable": {"enabled": True}},
                    }
                ],
                "access": {"storefront": "PUBLIC_READ"},
                "capabilities": {"translatable": {"enabled": True}},
            }
        }

        response = await self.shopify_client.query(mutation, variables)

        data = (
            response.get("data", {})
            .get("metaobjectDefinitionCreate", {})
            .get("metaobjectDefinition", {})
        )

        if not data:
            errors = (
                response.get("data", {})
                .get("metaobjectDefinitionCreate", {})
                .get("userErrors", [])
            )
            self.logger.error(f"Failed to create metaobject definition: {errors}")
            raise Exception(f"Metaobject definition creation failed: {errors}")

        object_id = data.get("id")
        object_type = data.get("type")

        if not object_id or not object_type:
            raise Exception(
                f"Metaobject definition creation succeeded, but missing fields ('id' or 'type') in response: {response}"
            )

        return {
            "id": object_id,
            "type": object_type,
            "values": {},
        }

    async def create_missing_values(
        self, definition_type: str, field_key: str, values: dict[str, str | None]
    ) -> dict[str, str | None]:

        for value_name, value_id in values.items():
            if value_id is not None:
                continue  # Skip values that already have an ID

            mutation = self._query_create_value()

            variables: dict[str, Any] = {
                "metaobject": {
                    "type": definition_type,
                    "fields": [{"key": field_key, "value": value_name}],
                }
            }

            response = await self.shopify_client.query(mutation, variables)

            data = (
                response.get("data", {})
                .get("metaobjectCreate", {})
                .get("metaobject", {})
            )

            if not data:
                errors = (
                    response.get("data", {})
                    .get("metaobjectCreate", {})
                    .get("userErrors", [])
                )
                self.logger.error(
                    f"Failed to create metaobject value '{value_name}': {errors}"
                )

            values[value_name] = data.get("id")

        return values

    async def _get_extra_values(self, definitions: dict[str, Any]) -> dict[str, Any]:
        for defn in definitions.values():
            if not defn["more_values"]:
                continue

            defn["values"] = {}

            cursor = None

            while True:
                query = self._query_get_values()
                variables: dict[str, Any] = {
                    "type": defn["type"],
                    "cursor": cursor,
                }

                response = await self.shopify_client.query(query, variables)

                data = response.get("data", {}).get("metaobjects", {})

                batch_data = data.get("edges", [])

                for item in batch_data:
                    entry = item.get("node", {})

                    entry_id = entry.get("id")
                    entry_handle = entry.get("handle")

                    defn["values"][entry_handle] = {
                        "id": entry_id,
                        "values": {
                            field.get("key"): field.get("value")
                            for field in entry.get("fields", [])
                        },
                    }

                if not data["pageInfo"]["hasNextPage"]:
                    break

                cursor = data["pageInfo"]["endCursor"]

                await sleep(
                    self.settings.SHOPIFY_API_BATCH_DELAY
                )  # Rate limiting delay

        return definitions

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

    @staticmethod
    def _query_get_values(query_name: str | None = None) -> str:
        """
        GraphQL query for fetching metaobject values from Shopify

        Query args:
            type: Metaobject type to filter by
            cursor: Pagination cursor for batching through results

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($type: String!, $cursor: String) {{
                metaobjects(type: $type, first: 250, after: $cursor) {{
                    edges {{
                        node {{
                            id
                            handle
                            fields {{
                                key
                                value
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

    @staticmethod
    def _query_create_definition(query_name: str | None = None) -> str:
        """
        GraphQL query for creating a metaobject definition in Shopify

        Query args:
            definition: Input object containing metaobject definition details

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            mutation {query_name if query_name else ""}($definition: MetaobjectDefinitionCreateInput!) {{
                metaobjectDefinitionCreate(definition: $definition) {{
                    metaobjectDefinition {{
                        id
                        type
                    }}
                    userErrors {{
                        field
                        message
                    }}
                }}
            }}
        """

    @staticmethod
    def _query_create_value(query_name: str | None = None) -> str:
        """
        GraphQL query for creating a metaobject value in Shopify

        Query args:
            metaobject: Input object containing metaobject value details, including type and field values

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            mutation {query_name if query_name else ""}($metaobject: MetaobjectCreateInput!) {{
                metaobjectCreate(metaobject: $metaobject) {{
                    metaobject {{
                        id
                        fields {{
                            key
                            value
                        }}
                    }}
                    userErrors {{
                        field
                        message
                    }}
                }}
            }}
        """
