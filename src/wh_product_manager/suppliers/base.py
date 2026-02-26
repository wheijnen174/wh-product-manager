"""
Base supplier class
Abstract base for all supplier implementations
"""

from abc import ABC, abstractmethod
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.country_mapping import (
    CountryMappingRepository,
)
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.suppliers.schemas import (
    SupplierDataResult,
    UnifiedProduct,
)


class BaseSupplier(ABC):
    """Abstract base class for all suppliers"""

    def __init__(
        self,
        name: str,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
        country_mapping_repo: CountryMappingRepository,
    ):
        """
        Initialize supplier

        Args:
            name: Name of the supplier
            shopify_client: ShopifyGraphQLClient instance
            settings: Application settings
            logger: Logger instance
            country_mapping_repo: CountryMappingRepository instance
        """
        self.name = name
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.country_mapping_repo = country_mapping_repo

    @abstractmethod
    async def fetch_raw_data(self) -> dict[str, Any]:
        """
        Fetch raw data from supplier API/source

        Returns:
            dict: Raw supplier data in native format
        """
        pass

    @abstractmethod
    async def transform_data(
        self, raw_data: dict[str, Any]
    ) -> dict[str, UnifiedProduct]:
        """
        Transform raw supplier data to unified format

        Args:
            raw_data: Raw data from supplier

        Returns:
            dict[str, UnifiedProduct]: Transformed products in unified format where key is parent SKU
        """
        pass

    async def get_unified_data(self) -> SupplierDataResult:
        """
        Fetch and transform supplier data in one step

        Returns:
            SupplierDataResult: Unified data result with status
        """
        try:
            self.logger.info(f"{self.name} - Fetching raw data...")
            raw_data = await self.fetch_raw_data()

            self.logger.info(f"{self.name} - Transforming data to unified format...")
            products = await self.transform_data(raw_data)

            self.logger.info(
                f"{self.name} - Successfully fetched and transformed {len(products)} products"
            )

            return SupplierDataResult(
                supplier_name=self.name,
                status="success",
                products=products,
                item_count=len(products),
            )

        except Exception as e:
            self.logger.error(f"{self.name} - Failed to get data: {str(e)}")
            return SupplierDataResult(
                supplier_name=self.name,
                status="failed",
                error=str(e),
                item_count=0,
            )

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate connection to supplier

        Returns:
            bool: True if connected successfully
        """
        pass
