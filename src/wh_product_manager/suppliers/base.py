"""
Base supplier class
Abstract base for all supplier implementations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.country_mapping import CountryMappingRepository
from wh_product_manager.products.schemas.product import UnifiedProduct
from wh_product_manager.settings import Settings
from wh_product_manager.shopify.client import ShopifyGraphQLClient


@dataclass
class SupplierDataResult:
    """Result of fetching and transforming supplier data"""

    supplier_name: str
    status: str  # "success" or "failed"
    item_count: int = 0
    error: Optional[str] = None
    products: Optional[dict[str, UnifiedProduct]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "supplier_name": self.supplier_name,
            "status": self.status,
            "item_count": self.item_count,
            "error": self.error,
            "products": {k: v.to_dict() for k, v in (self.products or {}).items()},
        }


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
    async def fetch_raw_data(self) -> tuple[str, dict[str, Any]]:
        """
        Fetch raw data from supplier API/source

        Returns:
            tuple[str, dict[str, Any]]: A tuple containing the last-seen timestamp and raw supplier data in native format
        """
        pass

    @abstractmethod
    async def transform_data(
        self, last_seen_at: str, raw_data: dict[str, Any]
    ) -> dict[str, UnifiedProduct]:
        """
        Transform raw supplier data to unified format

        Args:
            last_seen_at: The timestamp when this supplier snapshot was fetched
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
            last_seen_at, raw_data = await self.fetch_raw_data()

            self.logger.info(f"{self.name} - Transforming data to unified format...")
            products = await self.transform_data(last_seen_at, raw_data)

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
