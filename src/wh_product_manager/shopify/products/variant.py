"""
Shopify variant product operations
Manages creation, updating, and deletion of variant products
"""

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient


class ProductVariant:
    """Manages variant product operations"""

    def __init__(self, shopify_client: ShopifyGraphQLClient, logger: Logger):
        """
        Initialize variant product manager

        Args:
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.logger = logger
