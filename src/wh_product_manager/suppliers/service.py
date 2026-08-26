"""
Supplier Data Service
Orchestrates all supplier operations
"""

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.country_mapping import CountryMappingRepository
from wh_product_manager.settings import Settings
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.providers.Provider_1 import Supplier_Provider_1


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
        country_mapping_repo: CountryMappingRepository,
    ):
        """
        Initialize supplier service

        Args:
            shopify_client: ShopifyGraphQLClient instance
            settings: Application settings
            logger: Logger instance
            country_mapping_repo: CountryMappingRepository instance
        """

        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.country_mapping_repo = country_mapping_repo

        self.suppliers: dict[str, BaseSupplier] = {
            "Provider-1": Supplier_Provider_1(
                name="Provider 1",
                shopify_client=self.shopify_client,
                settings=self.settings,
                logger=self.logger,
                country_mapping_repo=self.country_mapping_repo,
            ),
        }

        self.logger.info(
            f"SupplierService initialized with suppliers: {list(self.suppliers.keys())}"
        )

    async def supplier_exists(self, supplier_name: str) -> bool:
        """
        Check if a supplier exists by name

        Args:
            supplier_name: Name of the supplier to check

        Returns:
            True if supplier exists, False otherwise
        """
        exists = supplier_name.lower() in [
            name.lower() for name in self.suppliers.keys()
        ]
        self.logger.debug(f"Checked existence of supplier '{supplier_name}': {exists}")
        return exists

    async def get_supplier(self, supplier_name: str) -> BaseSupplier:
        """
        Get supplier instance by name

        Args:
            supplier_name: Name of the supplier

        Returns:
            BaseSupplier instance
        """
        supplier = self.suppliers.get(supplier_name)

        if not supplier:
            self.logger.error(f"Supplier '{supplier_name}' not found")
            raise ValueError(f"Supplier '{supplier_name}' not found")

        self.logger.debug(f"Resolved supplier instance for '{supplier_name}'")

        return supplier
