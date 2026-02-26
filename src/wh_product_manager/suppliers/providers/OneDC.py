"""
Provider 1 Supplier
Fetches and transforms Provider 1 data to unified format
"""

from typing import Any

import httpx
import xmltodict

from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.suppliers.schemas import (
    UnifiedProduct,
    UnifiedProperty,
    UnifiedVariant,
)
from wh_product_manager.utils.formatters import (
    normalize_string,
    regex,
    string_needs_normalization,
)


class Supplier_OneDC(BaseSupplier):
    """Supplier implementation for Provider 1"""

    async def fetch_raw_data(self) -> dict[str, Any]:
        """
        Fetch raw data from Provider 1

        Returns:
            dict: Raw data from One-DC

        Raises:
            httpx.HTTPError: If the API request fails
        """
        try:
            # # Offline data for testing purposes
            # from wh_product_manager.utils.data_loader import get_data_dir

            # data_dir = get_data_dir()
            # with open(
            #     data_dir / "onedc_product_data_20260210.xml", "r", encoding="utf-8"
            # ) as file:
            #     xml_content = file.read()

            #     data = xmltodict.parse(xml_content)

            #     return data

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

    async def transform_data(
        self, raw_data: dict[str, Any]
    ) -> dict[str, UnifiedProduct]:
        """
        Transform Supplier One-DC's native format to unified format

        Args:
            raw_data: Raw data from Supplier One-DC

        Returns:
            dict[str, UnifiedProduct]: Transformed products where key is parent SKU
        """

        conversion_map: dict[
            str, str
        ] = await self.country_mapping_repo.map_name_to_iso()

        unified_products: dict[str, UnifiedProduct] = {}

        for product in raw_data.get("products", {}).get("product", []):
            try:
                valid_product = True

                price = float(product.get("prices").get("recommended_retail_price"))
                cost = float(product.get("prices").get("b2b_price"))
                weight = product.get("weight")

                if product.get("country_of_origin"):
                    country_name: str = product.get("country_of_origin")
                    if string_needs_normalization(country_name):
                        self.logger.debug(
                            f"{self.name} - Country name '{country_name}' needs normalization"
                        )
                        country_name = normalize_string(country_name)
                        self.logger.debug(
                            f"{self.name} - Normalized country name: '{country_name}'"
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
                    self.logger.warning(
                        f"{self.name} - Country of origin '{product.get('country_of_origin')}' not found in conversion map"
                    )

                hscode = int(product.get("hscode")) if product.get("hscode") else None

                # Transform variants
                variants_raw: list[dict[str, Any]] = product.get("variants", {}).get(
                    "variant", []
                )
                if isinstance(variants_raw, dict):
                    variants_raw = [variants_raw]  # Convert single variant to list

                if len(variants_raw) > 1 and set(
                    item.get("size_title") for item in variants_raw
                ) == {None}:
                    valid_product = False
                    self.logger.debug(
                        f"{self.name} - Product '{product.get('head_article_number')}' has multiple variants but no size titles, skipping product"
                    )

                variants: list[UnifiedVariant] = []
                for item in variants_raw:
                    barcode_raw: str | list[str] | None = item.get("barcode")
                    if isinstance(barcode_raw, list):
                        barcode = ",".join(barcode_raw)
                    else:
                        barcode = barcode_raw

                    variant = UnifiedVariant(
                        sku=str(item.get("article_number")),
                        stock=int(item.get("stock") or 0),
                        price=price,
                        cost=cost,
                        barcode=barcode if barcode is not None else None,
                        size_title=item.get("size_title"),
                        weight=int(weight) if weight is not None else None,
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
                    properties=self.transform_product_properties(product),
                )

                if valid_product:
                    unified_products[product.get("head_article_number")] = (
                        unified_product
                    )

            except Exception as e:
                self.logger.error(
                    f"{self.name} - Transformation failed for product '{product.get('head_article_number')}': {str(e)}"
                )
                raise

        return unified_products

    def transform_product_properties(
        self, product: dict[str, Any]
    ) -> dict[str, UnifiedProperty]:
        """
        Transform product properties from Supplier One-DC's native format to unified format

        Args:
            product: Product data in Supplier One-DC's native format

        Returns:
            dict[str, UnifiedProperty]: Dictionary of transformed properties
        """

        values_not_units: list[str | None] = [None, "Enkel", "Multi"]

        product_properties: dict[str, UnifiedProperty] = {}

        # Handle properties that are not within the properties tag but are still important to include (e.g. brand, material, etc.)
        properties_ccv_keys = {
            "bulletpoints": "Bulletpoints",
            "content": "Inhoud",
            "brand": "Merk",
            "popularity": "Populariteit",
            "materials": "Materialen",
        }

        for ccv_key in properties_ccv_keys.keys():
            match ccv_key:
                case "bulletpoints":
                    if product.get(ccv_key) is not None:
                        filtered_values = [
                            x.strip()
                            for x in str(product.get(ccv_key)).split("\n")
                            if x.strip() != ""
                        ]
                        filtered_values = [
                            (x[2:] if x[:2] == "- " else x) for x in filtered_values
                        ]
                        filtered_values = [
                            str(regex(x, "str")) for x in filtered_values
                        ]

                        product_properties[properties_ccv_keys[ccv_key]] = (
                            UnifiedProperty(
                                single_or_multi="multi",
                                field_type="metafield",
                                values=filtered_values,
                            )
                        )

                case "content":
                    if (
                        product.get(ccv_key) is not None
                        and product.get("content_unit") is not None
                        and product.get("content_unit") != "n.v.t."
                    ):
                        product_properties[properties_ccv_keys[ccv_key]] = (
                            UnifiedProperty(
                                single_or_multi="single",
                                field_type="metaobject",
                                values=str(regex(str(product.get(ccv_key)), "num"))
                                + " "
                                + str(product.get("content_unit")),
                            )
                        )

                case "brand":
                    product_properties[properties_ccv_keys[ccv_key]] = UnifiedProperty(
                        single_or_multi="single",
                        field_type="metaobject",
                        values=str(
                            regex(
                                product.get(ccv_key, {}).get("title") or "Merkloos",
                                "str",
                            )
                        ),
                    )

                case "popularity":
                    allowed_values = ["1", "2", "3", "4"]
                    if product.get(ccv_key) in allowed_values:
                        value = str(product.get(ccv_key))
                    else:
                        value = "1"

                    product_properties[properties_ccv_keys[ccv_key]] = UnifiedProperty(
                        single_or_multi="single",
                        field_type="metaobject",
                        values=value,
                    )

                case "materials":
                    if product.get(ccv_key) is not None:
                        if not isinstance(product[ccv_key]["material"], list):
                            product[ccv_key]["material"] = [
                                product[ccv_key]["material"]
                            ]

                        product_properties[properties_ccv_keys[ccv_key]] = (
                            UnifiedProperty(
                                single_or_multi="multi",
                                field_type="metaobject",
                                values=[
                                    str(regex(value["name"], "str"))
                                    for value in product[ccv_key]["material"]
                                ],
                            )
                        )

                case _:
                    pass

        # Handle properties within properties tag (if they exist)
        if product.get("properties") is not None:
            raw_properties: list[dict[str, Any]] = product.get("properties", {}).get(
                "property", []
            )
            if isinstance(raw_properties, dict):
                raw_properties = [raw_properties]  # Convert single property to list

            for raw_property in raw_properties:
                try:
                    property_title = str(raw_property.get("title"))
                    property_single_or_multi: str = (
                        "multi" if raw_property["type"] == "Multi" else "single"
                    )
                    property_field_type: str = "metaobject"

                    # Determine if the property is a unit-based property or a regular string property
                    property_unit = (
                        raw_property["type"]
                        if raw_property["type"] not in values_not_units
                        else None
                    )

                    if property_unit is None:
                        property_values = raw_property["values"]
                    else:
                        if isinstance(raw_property["values"], list):
                            property_values: str | list[str] = [
                                str(x)  # type: ignore
                                for x in raw_property["values"]  # type: ignore
                            ]

                            property_values = [
                                str(regex(item, "num")) + " " + property_unit
                                for item in property_values
                            ]

                        else:
                            property_values: str | list[str] = str(
                                raw_property["values"]
                            )

                            property_values = (
                                str(regex(raw_property["values"], "num"))
                                + " "
                                + property_unit
                            )

                    # Handle single vs multi values
                    if property_single_or_multi == "multi" and not isinstance(
                        property_values, list
                    ):
                        property_values = [property_values]
                    elif property_single_or_multi == "single" and isinstance(
                        property_values, list
                    ):
                        property_values = property_values[0]

                    if isinstance(property_values, list):
                        property_values = [
                            str(regex(x, "str")) for x in property_values if x != ""
                        ]
                    else:
                        property_values = str(regex(property_values, "str"))

                    if property_title == "Geschikt voor koppels":
                        property_values = (
                            [val.replace("Koppels: ", "") for val in property_values]
                            if isinstance(property_values, list)
                            else property_values.replace("Koppels: ", "")
                        )

                    # Only add property if it has values (not empty string or empty list)
                    if property_values != "" and property_values != [""]:
                        product_properties[property_title] = UnifiedProperty(
                            single_or_multi=property_single_or_multi,
                            field_type=property_field_type,
                            values=property_values,
                        )

                except Exception as e:
                    self.logger.error(
                        f"Supplier_OneDC - Failed to transform property '{raw_property.get('title')}' for product '{product.get('head_article_number')}': {str(e)}"
                    )

        return product_properties
