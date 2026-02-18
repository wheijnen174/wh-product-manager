"""
Shopify product set (parent + variant) operations
Manages creation, updating, and deletion of product sets
"""

from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.suppliers.schemas import UnifiedProduct


class ProductUpdate:
    """Manages product update operations"""

    def __init__(self, shopify_client: ShopifyGraphQLClient, logger: Logger):
        """
        Initialize product update manager

        Args:
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.logger = logger

    async def prepare_update_mutations(
        self,
        inventory: dict[str, Any],
        supplier_data: dict[str, UnifiedProduct],
        update_time: str,
    ) -> list[str]:
        mutation_items: list[str] = []

        for parent_sku, product in supplier_data.items():
            pass

        return mutation_items
