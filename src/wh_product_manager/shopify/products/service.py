"""
Shopify Product Service
Orchestrates all product operations
"""

from datetime import datetime, timezone
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.categories import CategoriesService
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.helpers.stock_location import StockLocation
from wh_product_manager.shopify.inventory import InventoryService
from wh_product_manager.shopify.product_properties import ProductPropertiesService
from wh_product_manager.shopify.products.product_create import ProductCreate
from wh_product_manager.shopify.products.product_update import ProductUpdate
from wh_product_manager.shopify.publishing import PublicationService
from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.schemas import UnifiedProduct
from wh_product_manager.suppliers.service import SupplierService


class ProductService:
    """
    Service for managing Shopify products
    Orchestrates product parent, product variant, and product set operations
    """

    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
        publication_service: PublicationService,
        inventory_service: InventoryService,
        supplier_service: SupplierService,
        categories_service: CategoriesService,
        product_properties_service: ProductPropertiesService,
    ):
        """
        Initialize product service

        Args:
            shopify_client: ShopifyGraphQLClient instance
            settings: Application settings
            logger: Logger instance
            publication_service: PublicationService instance
            inventory_service: InventoryService instance
            supplier_service: SupplierService instance
        """
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.publication_service = publication_service

        self.inventory_service = inventory_service
        self.supplier_service = supplier_service
        self.categories_service = categories_service
        self.product_properties_service = product_properties_service

        self.product_create = ProductCreate(shopify_client, logger)
        self.product_update = ProductUpdate(shopify_client, logger)

    async def create_products_for_supplier(
        self, supplier: BaseSupplier, new_products_limit: int | None = None
    ) -> dict[str, Any]:
        """
        Create products for a given supplier
        Orchestrates the creation of product parent, product variant, and product sets.

        Args:
            supplier: BaseSupplier instance to create products for
        """
        self.logger.info(f"Starting product creation for supplier: {supplier.name}")

        update_time = datetime.now(timezone.utc).isoformat()

        location_id = await StockLocation.get_id_by_name(
            supplier.name, self.shopify_client, self.logger
        )

        inventory, new_products, _ = await self._prepare_product_data(supplier)

        # Prepare and fetch categories. Create any new categories if needed
        categories = await self.categories_service.get_product_categories(new_products)

        # Prepare and fetch taxonomies
        category_constraints = await self.categories_service.get_category_constraints(
            product_type="product"
        )

        # Prepare and fetch product properties and put data in their place for each product
        new_products = await self.product_properties_service.process_properties(
            new_products, category_constraints
        )

        self.logger.info(
            f"Creating {len(new_products)} new products for supplier: {supplier.name}"
        )

        responses: list[dict[str, Any]] = []

        if new_products_limit is not None:
            new_products = dict(list(new_products.items())[:new_products_limit])
            self.logger.info(
                f"Limiting to {new_products_limit} new products for supplier: {supplier.name}"
            )

        for parent_sku, product in new_products.items():
            try:
                self.logger.debug(f"Creating product: '{parent_sku} - {product.title}'")

                necessary_categories = [
                    " > ".join(str(product.category).split(" > ")[: i + 1])
                    for i in range(len(str(product.category).split(" > ")))
                ]

                if not all(cat in categories for cat in necessary_categories):
                    missing_categories = [
                        cat for cat in necessary_categories if cat not in categories
                    ]
                    self.logger.warning(
                        f"Skipping product '{parent_sku}' - '{product.title}' due to missing categories: {missing_categories}"
                    )
                    continue  # Skip product creation if any category is missing

                product.extra_data["parent_sku"] = parent_sku
                product.extra_data["update_time"] = update_time
                product.extra_data["supplier_name"] = supplier.name

                product.extra_data["shopify_category"] = categories.get(
                    str(product.category), {}
                ).get("shopify_category")

                product.extra_data["shopify_collections"] = [
                    categories.get(str(cat), {}).get("collection_id")
                    for cat in necessary_categories
                ]

                response = await self.product_create.graphql_mutation__create(
                    product, location_id
                )

                responses.append(response)

            except Exception as e:
                self.logger.error(
                    f"Error creating product '{parent_sku} - {product.title}': {str(e)}"
                )

        product_ids_to_publish: list[str] = []
        for item in responses:
            for data in item.values():
                product_id = data.get("product_id")
                if product_id:
                    product_ids_to_publish.append(product_id)

        self.logger.info(f"Finished creating {len(product_ids_to_publish)} products")

        await self.publication_service.publish_shopify_objects(product_ids_to_publish)

        self.logger.info("Published new products")

        return {
            "found": len(inventory),
            "created": len(new_products),
            "response": responses,
        }

    async def update_products_for_supplier(
        self, supplier: BaseSupplier
    ) -> dict[str, Any]:
        """
        Update products in batches for a given supplier
        Orchestrates the update of parent and variant products

        Args:
            supplier: BaseSupplier instance to update products for
        """
        self.logger.info(f"Starting product update for supplier: {supplier.name}")

        update_time = datetime.now(timezone.utc).isoformat()

        # Fetch Shopify and supplier data
        # NOTE: This function already filters the supplier data to only contain products
        #       that are present in the inventory. Products in the inventory that are not present
        #       in the supplier data are not updated, but they are also not deleted.
        #       Handling of products that are not updated is done separately.
        inventory, _, supplier_data = await self._prepare_product_data(supplier)

        self.logger.info("Shopify and supplier data fetched.")

        # Prepare update mutations for all products that need to be updated
        self.logger.info(
            "Preparing update mutations for products that need to be updated."
        )
        mutation_items = await self.product_update.prepare_update_mutations(
            inventory, supplier_data, update_time
        )

        if len(mutation_items) == 0:
            self.logger.info("No products to update.")
            return {
                "found": len(inventory),
                "updated": 0,
                "updated_at": update_time,
                "execution_duration": None,
                "response": [],
            }

        # Prepare batches
        self.logger.info("Preparing mutation batches.")

        batch_size = 10
        batches: list[str] = []

        for i in range(0, len(mutation_items), batch_size):
            batch = mutation_items[i : i + batch_size]

            mutation = f"""
                mutation {{
                    {chr(10).join(batch)}
                }}
            """

            batches.append(mutation)

        # Execute batches
        self.logger.info(f"Executing {len(batches)} mutation batches.")

        zerofill = len(str(len(batches)))
        for idx, batch in enumerate(batches):
            logger_prefix = f"[Batch {str(idx + 1).zfill(zerofill)}/{len(batches)}]"
            try:
                self.logger.debug(f"{logger_prefix} Starting batch execution")
                # response = await self.shopify_client.execute(batch)
                response = "test response"
                self.logger.debug(f"{logger_prefix} Batch response: {response}")
            except Exception as e:
                self.logger.error(f"{logger_prefix} Error executing batch: {str(e)}")

        self.logger.info(f"Finished executing {len(batches)} mutation batches.")

        responses: list[dict[str, Any]] = []

        self.logger.info(f"Finished updating {len(supplier_data)} products")

        return {
            "found": len(inventory),
            "updated": len(supplier_data),
            "updated_at": update_time,
            "execution_duration": None,
            "response": responses,
        }

    async def _prepare_product_data(
        self, supplier: BaseSupplier
    ) -> tuple[dict[str, Any], dict[str, UnifiedProduct], dict[str, UnifiedProduct]]:
        """
        Prepare product data for creation and update
        Fetches supplier data and current inventory to determine which products need to be created or updated

        Args:
            supplier: BaseSupplier instance to prepare product data for

        Returns:
            tuple: Prepared product data categorized into new and existing products
                    (
                        inventory: dict[str, Any],
                        new_products: dict[str, UnifiedProduct],
                        existing_products: dict[str, UnifiedProduct]
                    )
        """

        supplier_name = supplier.name

        inventory = await self.inventory_service.get_current_inventory(
            supplier=supplier_name, return_ids=True
        )

        supplier_data = await supplier.get_unified_data()

        if supplier_data.products is None:
            self.logger.warning(f"No products found for supplier: {supplier_name}")
            return {}, {}, {}

        new_products = {
            k: v for k, v in supplier_data.products.items() if k not in inventory.keys()
        }
        existing_products = {
            k: v for k, v in supplier_data.products.items() if k in inventory.keys()
        }

        return inventory, new_products, existing_products
