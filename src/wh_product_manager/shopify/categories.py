from asyncio import sleep
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.collections import CollectionsRepository
from wh_product_manager.db.models.shopify_category_taxonomies import (
    ShopifyCategoryTaxonomiesRepository,
)
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.publishing import PublicationService
from wh_product_manager.suppliers.schemas import UnifiedProduct


class CategoriesService:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
        publication_service: PublicationService,
        shopify_category_taxonomies_repo: ShopifyCategoryTaxonomiesRepository,
        collections_repo: CollectionsRepository,
    ):
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.publication_service = publication_service
        self.shopify_category_taxonomies_repo = shopify_category_taxonomies_repo
        self.collections_repo = collections_repo

    async def get_product_categories(
        self, products: dict[str, UnifiedProduct]
    ) -> dict[str, Any]:
        categories = await self._load_categories_file()

        existing_categories = await self._existing_categories(
            self.shopify_client, self.settings, self.logger
        )

        necessary_categories = await self._necessary_categories(products, self.logger)

        # Update categories file with data from Shopify categories (update missing ID's and handles)
        for breadcrumbs, details in existing_categories.items():
            if breadcrumbs in categories:
                categories[breadcrumbs]["name"] = details["name"]
                categories[breadcrumbs]["collection_id"] = details["collection_id"]
                categories[breadcrumbs]["handle"] = details["handle"]
                categories[breadcrumbs]["level"] = details["level"]

            else:
                categories[breadcrumbs] = details

        for breadcrumbs in [
            crumb for crumb in categories if crumb not in existing_categories
        ]:
            categories[breadcrumbs]["collection_id"] = None
            categories[breadcrumbs]["handle"] = None

        # Determine which necessary categories are new (not in existing categories) and then create the new categories
        for breadcrumbs, details in necessary_categories.items():
            if breadcrumbs not in categories:
                categories[breadcrumbs] = details

        new_categories = {
            breadcrumbs: details
            for breadcrumbs, details in categories.items()
            if details["collection_id"] is None
        }

        if len(new_categories) > 0:
            publish_object_ids: list[str] = []

            self.logger.info(f"Creating {len(new_categories)} new categories")

            #  Note:  creating new collections in batch is 2/3 faster than creating them one by one,
            #         but for simplicity, we will create them one by one for now. In most situations there are
            #         only a few new categories, so the performance difference is negligible.
            for breadcrumbs, details in new_categories.items():
                # Create new category and add Shopify details to existing categories dict (which will be used for product creation)
                new_details = await self._create_category(
                    breadcrumbs, details, self.shopify_client, self.logger
                )
                categories[breadcrumbs]["name"] = new_details["name"]
                categories[breadcrumbs]["collection_id"] = new_details["collection_id"]
                categories[breadcrumbs]["handle"] = new_details["handle"]
                categories[breadcrumbs]["level"] = new_details["level"]

                # Add new category ID to list of objects to publish
                publish_object_ids.append(new_details["collection_id"])

            self.logger.info(
                f"Created {len(new_categories)} new categories, now publishing all new categories"
            )

            await self.publication_service.publish_shopify_objects(
                object_ids=publish_object_ids,
            )

            self.logger.info(f"Published {len(publish_object_ids)} new categories")

        else:
            self.logger.debug("No new categories to create")

        # Save the updated categories file with new categories and updated details from Shopify
        await self._save_categories_file(categories)

        # Checking for categories with missing details which are necessary for product creation. These categories are unusable and will be logged as warnings
        categories_missing_details = {
            breadcrumbs: details
            for breadcrumbs, details in categories.items()
            if None in details.values()
        }

        if len(categories_missing_details) > 0:
            # TODO: implement notification mailing for missing details.

            self.logger.warning(
                f"{len(categories_missing_details)} categories are missing Shopify details and are unusable: {list(categories_missing_details.keys())}"
            )

        usable_categories = {
            breadcrumbs: details
            for breadcrumbs, details in categories.items()
            if None not in details.values()
        }

        return usable_categories

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

            response = await self.shopify_client.run(query, variables)

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

        response = await self.shopify_client.run(mutation, variables)

        data = (
            response.get("data", {}).get("collectionCreate", {}).get("collection", {})
        )

        details["collection_id"] = data.get("id")
        details["handle"] = data.get("handle")

        return details

    async def _load_categories_file(self) -> dict[str, dict[str, str | int | None]]:
        data = await self.collections_repo.get_all()
        return data

    async def _save_categories_file(
        self, data: dict[str, dict[str, str | int | None]]
    ) -> None:
        await self.collections_repo.save_all(data)

    async def get_category_constraints(self, product_type: str) -> list[str]:
        """
        Fetches the category constraints for product metafields from Shopify.

        This method retrieves the metafield definitions for products and extracts any category constraints defined in the metafield definition's description or a specific field. The constraints are expected to be in a specific format (e.g., JSON or a delimited string) that can be parsed to determine which categories are allowed for certain metafields.

        Args:
            product_type: The type of category constraints to fetch. Only "product" or "event" types are valid.
        Returns:
            list[str]: A list of category constraints for product metafields.
        """
        if product_type == "product":
            taxonomies = await self.shopify_category_taxonomies_repo.get_all()

            taxonomies.remove("ae-1")  # Remove event category from product constraints

            return taxonomies

        elif product_type == "event":
            return ["ae-1"]

        else:
            raise ValueError(
                f"Invalid category constraint type: {product_type}. Must be 'product' or 'event'."
            )

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
