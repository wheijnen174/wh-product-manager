"""
Supplier Data Service
Orchestrates all supplier operations
"""

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.providers.OneDC import Supplier_OneDC


class SupplierService:
    """
    Service for managing suppliers
    Orchestrates supplier operations
    """

    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
    ):
        """
        Initialize supplier service

        Args:
            shopify_client: ShopifyGraphQLClient instance
            settings: Application settings
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger

        self.suppliers: dict[str, BaseSupplier] = {
            "One-DC": Supplier_OneDC(self.shopify_client, self.settings, self.logger),
        }

        self.logger.info(
            f"SupplierService initialized with suppliers: {list(self.suppliers.keys())}"
        )
