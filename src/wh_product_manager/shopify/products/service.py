"""
Shopify Product Service
Orchestrates all product operations
"""

from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.parent import ParentProductManager
from wh_product_manager.shopify.products.variant import VariantProductManager


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

        # Initialize sub-managers
        self.parent = ParentProductManager(shopify_client, logger)
        self.variant = VariantProductManager(shopify_client, logger)

    async def create_product_with_variants(
        self,
        product_data: dict[str, Any],
        variants: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create a product parent and its variants

        Args:
            product_data: Parent product data
            variants: List of variant data

        Returns:
            dict: Summary of created product and variants
        """
        self.logger.info("Creating product with variants...")

        try:
            # Create parent product
            parent_result = await self.parent.create_product(product_data)
            product_id = parent_result["product"]["id"]
            self.logger.info(f"Created parent product: {product_id}")

            # Create variants
            created_variants: list[dict[str, Any]] = []
            for variant_data in variants:
                variant_result = await self.variant.create_variant(
                    product_id, variant_data
                )
                created_variants.append(variant_result["productVariant"])
                self.logger.info(
                    f"Created variant: {variant_result['productVariant']['id']}"
                )

            return {
                "status": "success",
                "product_id": product_id,
                "variants_created": len(created_variants),
                "variants": created_variants,
            }

        except Exception as e:
            self.logger.error(f"Failed to create product with variants: {str(e)}")
            raise

    async def disable_stale_products(
        self, products: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Disable products older than grace period

        Args:
            products: List of product dictionaries

        Returns:
            dict: Summary of disabled products
        """
        grace_period = self.settings.PRODUCT_GRACE_PERIOD_IN_DAYS
        return await self.parent.disable_stale_products(products, grace_period)
