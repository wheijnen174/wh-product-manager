"""
Supplier Data Service
Orchestrates all supplier operations
"""

from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.providers.OneDC import Supplier_OneDC
from wh_product_manager.suppliers.schemas import SupplierDataResult


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
            "one-dc": Supplier_OneDC(self.shopify_client, self.settings, self.logger),
        }

        self.logger.info(
            f"SupplierService initialized with suppliers: {list(self.suppliers.keys())}"
        )

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

        return supplier

    async def fetch_all_data(self) -> dict[str, Any]:
        """
        Fetch raw product data from all suppliers

        Returns:
            Dictionary mapping supplier names to their raw product data
        """
        self.logger.info("Fetching raw product data from all suppliers")
        all_data: dict[str, Any] = {}

        for name, supplier in self.suppliers.items():
            self.logger.info(f"Fetching data from supplier: {name}")
            try:
                data = await supplier.get_unified_data()
                all_data[name] = data
                self.logger.info(f"Successfully fetched data from {name}")
            except Exception as e:
                self.logger.error(f"Error fetching data from {name}: {str(e)}")
                all_data[name] = SupplierDataResult(
                    supplier_name=name, status="failed", error=str(e)
                )

        return all_data
