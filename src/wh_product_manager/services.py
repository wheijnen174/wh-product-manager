"""
Dependency injection container
Initializes and manages all services
"""

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.inventory import InventoryService
from wh_product_manager.shopify.products import ProductService
from wh_product_manager.shopify.publishing import Publications
from wh_product_manager.suppliers.service import SupplierService


class Services:
    """
    Dependency injection container for all services
    Instantiates all managers and helpers
    """

    def __init__(self, settings: Settings):
        """
        Initialize the container with all dependencies

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = Logger(level=settings.LOG_LEVEL)

        self.shopify_client = ShopifyGraphQLClient(settings, self.logger)

        self.publications = Publications(self.shopify_client, self.logger)

        self.shopify_inventory = InventoryService(
            self.shopify_client, self.settings, self.logger
        )

        self.product_service = ProductService(
            self.shopify_client, settings, self.logger, self.publications
        )

        self.supplier_service = SupplierService(
            self.shopify_client, settings, self.logger
        )

        self.logger.info("Services Container initialized with all services")
