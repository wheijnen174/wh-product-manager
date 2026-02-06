"""
Dependency injection container
Initializes and manages all services
"""

from .config import Settings
from .core.logger import Logger


class Container:
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
        self.logger = Logger(settings.LOG_LEVEL)

        # Core services
        # self.shopify_client = ShopifyGraphQLClient(
        #     shop_url=settings.SHOPIFY_URL,
        #     access_token=settings.SHOPIFY_ACCESS_TOKEN,
        #     logger=self.logger,
        # )

        # Helpers
        # self.helpers = ShopifyHelpers(self.shopify_client, self.logger)
        self.logger.info("Container initialized with all services")
