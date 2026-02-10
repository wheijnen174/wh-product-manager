"""
Shopify Product Service
Orchestrates all product operations
"""

from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.inventory import InventoryService
from wh_product_manager.shopify.products.parent import ProductParent
from wh_product_manager.shopify.products.variant import ProductVariant
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

        self.inventory_service = InventoryService(shopify_client, settings, logger)
        self.supplier_service = SupplierService(shopify_client, settings, logger)

        # Initialize sub-managers
        self.parent = ProductParent(shopify_client, logger)
        self.variant = ProductVariant(shopify_client, logger)

    async def create_products_for_supplier(self, supplier_name: str):
        """
        Create products for a given supplier
        Orchestrates the creation of parent and variant products

        Args:
            supplier_name: Name of the supplier to create products for
        """
        self.logger.info(f"Starting product creation for supplier: {supplier_name}")

        inventory, new_products, existing_products = await self._prepare_product_data(
            supplier_name
        )

        return {
            "found": len(inventory),
            "created": len(new_products),
            "skipped": len(existing_products),
        }

    async def update_products_for_supplier(self, supplier_name: str):
        """
        Update products for a given supplier
        Orchestrates the update of parent and variant products

        Args:
            supplier_name: Name of the supplier to update products for
        """
        self.logger.info(f"Starting product update for supplier: {supplier_name}")

        inventory, _, existing_products = await self._prepare_product_data(
            supplier_name
        )

        return {
            "found": len(inventory),
            "updated": len(existing_products),
        }

    async def _prepare_product_data(
        self, supplier_name: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """
        Prepare product data for creation and update
        Fetches supplier data and current inventory to determine which products need to be created or updated

        Args:
            supplier_name: Name of the supplier to prepare product data for

        Returns:
            tuple: Prepared product data categorized into new and existing products
                    (
                        inventory: dict[str, Any],
                        new_products: dict[str, Any],
                        existing_products: dict[str, Any]
                    )
        """

        inventory = await self.inventory_service.get_current_inventory(
            supplier=supplier_name, return_ids=True
        )

        supplier = await self.supplier_service.get_supplier(supplier_name)
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
