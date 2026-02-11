from asyncio import sleep
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.publishing import Publications
from wh_product_manager.suppliers.schemas import UnifiedProduct
from wh_product_manager.utils.data_loader import load_json, save_json


class Categories:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
        publications: Publications,
        products: dict[str, UnifiedProduct],
    ):
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.publications = publications
        self.products = products

    async def get_categories(self) -> dict[str, Any]:
        existing_categories = await self._existing_categories(
            self.shopify_client, self.settings, self.logger
        )

        necessary_categories = await self._necessary_categories(
            self.products, self.logger
        )

        new_categories = {
            breadcrumbs: details
            for breadcrumbs, details in necessary_categories.items()
            if breadcrumbs not in existing_categories
        }

        # TODO: Implement the 'collections.json' file data processing!

        publish_object_ids: list[str] = []

        self.logger.info(f"Creating {len(new_categories)} new categories")

        for breadcrumbs, details in new_categories.items():
            # Create new category and add Shopify details to existing categories dict (which will be used for product creation)
            new_details = await self._create_category(
                breadcrumbs, details, self.shopify_client, self.logger
            )
            existing_categories[breadcrumbs] = new_details

            # Add new category ID to list of objects to publish
            publish_object_ids.append(new_details["collection_id"])

        self.logger.info(
            f"Created {len(new_categories)} new categories, now publishing all new categories"
        )

        await self.publications.publish_shopify_objects(
            object_ids=publish_object_ids,
            shopify_client=self.shopify_client,
            logger=self.logger,
        )

        self.logger.info(f"Published {len(publish_object_ids)} new categories")

        categories = {
            breadcrumbs: details
            for breadcrumbs, details in existing_categories.items()
            if None not in details.values()
        }

        categories_missing_details = {
            breadcrumbs: details
            for breadcrumbs, details in existing_categories.items()
            if None in details.values()
        }

        if len(categories_missing_details) > 0:
            self.logger.warning(
                f"{len(categories_missing_details)} categories are missing Shopify details and will be skipped: {list(categories_missing_details.keys())}"
            )

        raise NotImplementedError(
            "Einde! Debug: Check necessary categories before proceeding"
        )  # Debug: Stop execution to check necessary categories

        return categories

    async def _existing_categories(
        self, shopify_client: ShopifyGraphQLClient, settings: Settings, logger: Logger
    ) -> dict[str, Any]:
        query = self._query_get_categories()

        cursor = None

        existing_categories: dict[str, Any] = {}

        while True:
            variables: dict[str, Any] = {
                "cursor": cursor,
            }

            response = await self.shopify_client.query(query, variables)

            data = response.get("data", {}).get("collections", {})

            batch_data = data.get("edges", [])

            for item in batch_data:
                breadcrumbs = next(
                    (
                        metafield["value"]
                        for metafield in item["node"]["metafields"]["nodes"]
                        if metafield["key"] == "whpm.collection_breadcrumbs"
                    ),
                    None,
                )
                name = item["node"]["title"]
                collection_id = item["node"]["id"]
                handle = item["node"]["handle"]
                level = next(
                    (
                        metafield["value"]
                        for metafield in item["node"]["metafields"]["nodes"]
                        if metafield["key"] == "whpm.collection_level"
                    ),
                    None,
                )

                if (
                    breadcrumbs is not None
                    and level is not None
                    and breadcrumbs not in existing_categories
                ):
                    existing_categories[breadcrumbs] = {
                        "name": name,
                        "shopify_category": None,
                        "collection_id": collection_id,
                        "handle": handle,
                        "level": int(level),
                    }

            if not data["pageInfo"]["hasNextPage"]:
                break

            cursor = data["pageInfo"]["endCursor"]

            await sleep(self.settings.SHOPIFY_API_BATCH_DELAY)  # Rate limiting delay

        return dict(sorted(existing_categories.items()))

    async def _necessary_categories(
        self, products: dict[str, UnifiedProduct], logger: Logger
    ) -> dict[str, Any]:
        necessary_categories: dict[str, Any] = {}

        for product in products.values():
            if product.category is not None:
                # If category or each of the parent categories is not already in existing categories, add it to necessary categories
                categories_to_add = [
                    " > ".join(product.category.split(" > ")[: i + 1])
                    for i in range(len(product.category.split(" > ")))
                ]
                for category in categories_to_add:
                    if category not in necessary_categories:
                        name = category.split(" > ")[-1].strip()
                        level = len(category.split(" > "))

                        necessary_categories[category] = {
                            "name": name,
                            "shopify_category": None,
                            "collection_id": None,
                            "handle": None,
                            "level": level,
                        }

        return dict(sorted(necessary_categories.items()))

    async def _create_category(
        self,
        breadcrumbs: str,
        details: dict[str, Any],
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
    ) -> dict[str, Any]:
        mutation = self._mutation_create_category()
        variables: dict[str, Any] = {
            "input": {
                "title": details["name"],
                "metafields": [
                    {
                        "namespace": "whpm",
                        "key": "collection_breadcrumbs",
                        "value": breadcrumbs,
                    },
                    {
                        "namespace": "whpm",
                        "key": "collection_level",
                        "value": str(details["level"]),
                    },
                ],
            }
        }

        response = await self.shopify_client.query(mutation, variables)

        data = (
            response.get("data", {}).get("collectionCreate", {}).get("collection", {})
        )

        details["collection_id"] = data.get("id")
        details["handle"] = data.get("handle")

        return details

    async def _load_categories_file(self) -> dict[str, dict[str, str | int]]:
        data = load_json("collections.json")
        return data

    async def _update_categories_file(
        self, data: dict[str, dict[str, str | int]]
    ) -> None:
        save_json("collections.json", data)

    @staticmethod
    def _mutation_create_category(mutation_name: str | None = None) -> str:
        """
        GraphQL mutation for creating a category

        Query args:
            input: CollectionInput object containing category details

        Args:
            mutation_name: Optional name for the mutation (for batching/debugging)
        Returns:
            str: GraphQL mutation string
        """

        return f"""
            mutation {mutation_name if mutation_name else ""}($input: CollectionInput!) {{
                collectionCreate(input: $input) {{
                    collection {{
                        id
                        handle
                    }}
                    userErrors {{
                        field
                        message
                    }}
                }}
            }}
        """

    @staticmethod
    def _query_get_categories(query_name: str | None = None) -> str:
        """
        GraphQL query for fetching categories

        Query args:
            input: CollectionInput object containing category details

        Args:
            query_name: Optional name for the query (for batching/debugging)
        Returns:
            str: GraphQL query string
        """

        return f"""
            query {query_name if query_name else ""}($cursor: String) {{
                collections(first: 250, after: $cursor) {{
                    edges {{
                        node {{
                            id
                            title
                            handle
                            metafields(first: 2, keys: ["whpm.collection_breadcrumbs", "whpm.collection_level"]) {{
                                nodes {{
                                    key
                                    value
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
