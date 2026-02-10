"""
Provider 1 Supplier
Fetches and transforms Provider 1 data to unified format
"""

from typing import Any

import httpx
import xmltodict

from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.helpers.countryname_conversion import (
    CountrynameConversion,
)
from wh_product_manager.suppliers.schemas import UnifiedProduct, UnifiedVariant
from wh_product_manager.utils.formatters import (
    normalize_string,
    string_needs_normalization,
)


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
            # Offline data for testing purposes
            from wh_product_manager.utils.data_loader import get_assets_dir

            assets_dir = get_assets_dir()
            with open(assets_dir / "onedc_product_data_20260210.xml", "r") as file:
                xml_content = file.read()

                data = xmltodict.parse(xml_content)

                return data

            # # Actual internet-fetching disabled for testing purposes, return offline data instead
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(
            #         self.settings.ONEDC_XML_URL,
            #         timeout=30.0,
            #     )
            #     response.raise_for_status()

            #     data = xmltodict.parse(response.text)

            #     return data

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

        conversion_map = CountrynameConversion.map_name_to_iso(self.logger)

        import json

        json.dumps(conversion_map)

        try:
            self.logger.info("Supplier_OneDC - Transforming data...")
            unified_products: dict[str, UnifiedProduct] = {}

            for product in raw_data.get("products", {}).get("product", []):
                # Set values for common fields for all variants
                price = float(product.get("prices").get("recommended_retail_price"))
                cost = float(product.get("prices").get("b2b_price"))
                weight = product.get("weight")

                if product.get("country_of_origin"):
                    country_name: str = product.get("country_of_origin")
                    if string_needs_normalization(country_name):
                        self.logger.debug(
                            f"Supplier_OneDC - Country name '{country_name}' needs normalization"
                        )
                        country_name = normalize_string(country_name)
                        self.logger.debug(
                            f"Supplier_OneDC - Normalized country name: '{country_name}'"
                        )

                    country_of_origin = conversion_map.get(country_name.lower())
                else:
                    country_of_origin = None

                country_of_origin = (
                    country_of_origin.upper() if country_of_origin else None
                )

                if (
                    country_of_origin is None
                    and product.get("country_of_origin") is not None
                ):
                    print(
                        f"Country name '{country_name}' needs normalization: ",
                        string_needs_normalization(country_name),
                        ". Normalized name: ",
                        normalize_string(country_name),
                    )
                    # self.logger.warning(
                    #     f"Supplier_OneDC - Country of origin '{country_name}' not found in conversion map"
                    # )

                hscode = int(product.get("hscode")) if product.get("hscode") else None

                # Transform variants
                variants_raw: list[dict[str, Any]] = product.get("variants", {}).get(
                    "variant", []
                )
                if isinstance(variants_raw, dict):
                    variants_raw = [variants_raw]  # Convert single variant to list

                variants: list[UnifiedVariant] = []
                for item in variants_raw:
                    variant = UnifiedVariant(
                        sku=str(item.get("article_number")),
                        stock=int(item.get("stock") or 0),
                        price=price,
                        cost=cost,
                        barcode=item.get("barcode"),
                        size_title=item.get("size_title"),
                        weight=weight,
                        country_of_origin=country_of_origin,
                        hscode=hscode,
                    )
                    variants.append(variant)

                # Handle images (convert single image to list if necessary)
                images: list[str] | str | None = None
                if product.get("images", {}):
                    images = product.get("images", {}).get("image")
                    if isinstance(images, str):
                        images = [images]

                # Handle categories (convert single category to list if necessary)
                categories: str | None = None
                if product.get("categories", {}).get("category"):
                    categories_raw = product.get("categories", {}).get("category", [])
                    if isinstance(categories_raw, dict):
                        categories_raw: list[dict[str, Any]] = [categories_raw]

                    categories = " > ".join([x["title"] for x in categories_raw])

                # Create unified product
                unified_product = UnifiedProduct(
                    supplier_product_id=product.get("pid"),
                    title=product.get("title"),
                    images=images,
                    category=categories,
                    variants=variants,
                    description=product.get("description"),
                    properties=None,
                )

                unified_products[product.get("head_article_number")] = unified_product

            self.logger.info(
                f"Supplier_OneDC - Transformed {len(unified_products)} products"
            )
            return unified_products

        except Exception as e:
            self.logger.error(f"Supplier_OneDC - Transformation failed: {str(e)}")
            raise
