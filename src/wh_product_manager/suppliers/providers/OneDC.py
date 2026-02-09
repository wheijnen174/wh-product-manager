"""
Provider 1 Supplier
Fetches and transforms Provider 1 data to unified format
"""

from typing import Any

import httpx
import xmltodict

from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.schemas import UnifiedProduct


class Supplier_OneDC(BaseSupplier):
    """Supplier implementation for Provider 1"""

    async def validate_connection(self) -> bool:
        """
        Validate connection to Provider 1

        Returns:
            bool: True if connected
        """
        try:
            self.logger.info("Supplier_OneDC - Validating connection...")
            # TODO: Add your connection validation logic
            # Example: Test API call, database connection, etc.
            return True
        except Exception as e:
            self.logger.error(f"Supplier_OneDC - Connection failed: {str(e)}")
            return False

    async def fetch_raw_data(self) -> dict[str, Any]:
        """
        Fetch raw data from Provider 1

        Returns:
            dict: Raw data from One-DC

        Raises:
            httpx.HTTPError: If the API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.settings.ONEDC_XML_URL,
                    timeout=30.0,
                )
                response.raise_for_status()

                data = xmltodict.parse(response.text)

                return data

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP request failed: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch raw data from One-DC: {str(e)}")
            raise

    def transform_data(self, raw_data: dict[str, Any]) -> dict[str, UnifiedProduct]:
        """
        Transform Supplier One-DC's native format to unified format

        Args:
            raw_data: Raw data from Supplier One-DC

        Returns:
            dict[str, UnifiedProduct]: Transformed products where key is parent SKU
        """

        return {"product1": None}  # TODO: Implement transformation logic

    #     try:
    #         self.logger.info("Supplier_OneDC - Transforming data...")
    #         unified_products = []

    #         for product in raw_data.get("products", []):
    #             # Transform variants
    #             variants = []
    #             for item in product.get("items", []):
    #                 variant = UnifiedVariant(
    #                     sku=item["item_sku"],
    #                     title=item["item_name"],
    #                     price=float(item["selling_price"]),
    #                     cost=float(item["cost_price"]),
    #                     quantity=int(item["stock"]),
    #                     barcode=item.get("barcode"),
    #                 )
    #                 variants.append(variant)

    #             # Create unified product
    #             last_updated = None
    #             if product.get("last_update"):
    #                 try:
    #                     last_updated = datetime.fromisoformat(
    #                         product["last_update"].replace("Z", "+00:00")
    #                     )
    #                 except ValueError:
    #                     pass

    #             unified_product = UnifiedProduct(
    #                 parent_sku=product["id"],
    #                 title=product["name"],
    #                 description=product.get("description"),
    #                 category=product.get("category"),
    #                 variants=variants,
    #                 metadata={
    #                     "provider": "Supplier_OneDC",
    #                     "original_id": product["id"],
    #                 },
    #                 last_updated=last_updated,
    #             )
    #             unified_products.append(unified_product)

    #         self.logger.info(
    #             f"Supplier_OneDC - Transformed {len(unified_products)} products"
    #         )
    #         return unified_products

    #     except Exception as e:
    #         self.logger.error(f"Supplier_OneDC - Transformation failed: {str(e)}")
    #         raise
