"""
Shopify Product Service
Orchestrates all product operations
"""

from datetime import datetime, timezone
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.categories import Categories
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.inventory import InventoryService
from wh_product_manager.shopify.products.parent import ProductParent
from wh_product_manager.shopify.products.variant import ProductVariant
from wh_product_manager.shopify.publishing import Publications
from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.schemas import UnifiedProduct
from wh_product_manager.suppliers.service import SupplierService


class ProductService:
    """
    Service for managing Shopify products
    Orchestrates parent and variant product operations
    """

    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
        publications: Publications,
    ):
        """
        Initialize product service

        Args:
            shopify_client: ShopifyGraphQLClient instance
            settings: Application settings
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.publications = publications

        self.inventory_service = InventoryService(shopify_client, settings, logger)
        self.supplier_service = SupplierService(shopify_client, settings, logger)

        # Initialize sub-managers
        self.parent = ProductParent(shopify_client, logger)
        self.variant = ProductVariant(shopify_client, logger)

    async def create_products_for_supplier(
        self, supplier: BaseSupplier
    ) -> dict[str, Any]:
        """
        Create products for a given supplier
        Orchestrates the creation of parent and variant products

        Args:
            supplier: BaseSupplier instance to create products for
        """
        self.logger.info(f"Starting product creation for supplier: {supplier.name}")

        inventory, new_products, existing_products = await self._prepare_product_data(
            supplier
        )

        update_time = datetime.now(timezone.utc).isoformat()

        # Prepare and fetch categories. Create any new categories if needed
        categories_manager = Categories(
            self.shopify_client,
            self.settings,
            self.logger,
            self.publications,
            new_products,
        )

        categories = await categories_manager.get_categories()  # type: ignore  # noqa: F841
        raise NotImplementedError("Category management not implemented yet")

        responses: list[dict[str, Any]] = []

        for parent_sku, product in new_products.items():
            self.logger.info(f"Creating product: '{parent_sku} - {product.title}'")

            product.parent_sku = parent_sku
            product.update_time = update_time
            product.supplier_name = (
                supplier.name
            )  # Set supplier_name for GraphQL creation

            response = await self.parent.graphql_create(product)
            responses.append(response)

            break  # Remove this break after finishing the actual creation logic

        return {
            "found": len(inventory),
            "created": len(new_products),
            "skipped": len(existing_products),
            "response": responses,
        }

    async def update_products_for_supplier(
        self, supplier: BaseSupplier
    ) -> dict[str, Any]:
        """
        Update products for a given supplier
        Orchestrates the update of parent and variant products

        Args:
            supplier: BaseSupplier instance to update products for
        """
        self.logger.info(f"Starting product update for supplier: {supplier.name}")

        inventory, _, existing_products = await self._prepare_product_data(supplier)

        update_time = datetime.now(timezone.utc).isoformat()

        return {
            "found": len(inventory),
            "updated": len(existing_products),
            "updated_at": update_time,
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
