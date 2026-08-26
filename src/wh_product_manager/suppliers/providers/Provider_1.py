"""
Provider 1 Supplier
Fetches and transforms Provider 1 data to unified format
"""

from datetime import datetime, timezone  # type: ignore # noqa: F401
from typing import Any, Optional

import httpx
import xmltodict
from slugify import slugify

from wh_product_manager.products.schemas.media import UnifiedMedia
from wh_product_manager.products.schemas.product import UnifiedProduct
from wh_product_manager.products.schemas.variant import UnifiedVariant
from wh_product_manager.properties.schemas.definition import UnifiedPropertyDefinition
from wh_product_manager.properties.schemas.value import UnifiedPropertyValue
from wh_product_manager.suppliers.base import BaseSupplier
from wh_product_manager.utils.formatters import (
    normalize_string,
    regex,
    string_needs_normalization,
)

dates: list[tuple[datetime, str]] = [
    (
        datetime(2026, 2, 10, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260210.xml",
    ),
    (
        datetime(2026, 2, 19, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260219.xml",
    ),
    (
        datetime(2026, 3, 5, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260305.xml",
    ),
    (
        datetime(2026, 3, 11, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260311.xml",
    ),
    (
        datetime(2026, 3, 12, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260312.xml",
    ),
    (
        datetime(2026, 3, 13, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260313.xml",
    ),
    (
        datetime(2026, 3, 15, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260315.xml",
    ),
    (
        datetime(2026, 4, 23, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260423.xml",
    ),
    (
        datetime(2026, 5, 8, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260508.xml",
    ),
    (
        datetime(2026, 5, 11, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260511.xml",
    ),
    (
        datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
        "provider1_product_data_20260701.xml",
    ),
]


class Supplier_Provider_1(BaseSupplier):
    """Supplier implementation for Provider 1"""

    async def fetch_raw_data(self) -> tuple[str, dict[str, Any]]:
        """
        Fetch raw data from Provider 1

        Returns:
            dict: Raw data from Provider 1

        Raises:
            httpx.HTTPError: If the API request fails
        """

        try:
            # Offline data for testing purposes
            from wh_product_manager.utils.data_loader import get_data_dir

            last_seen_at, filename = dates[5]  # 0 t/m (10 or -1)

            data_dir = get_data_dir()
            with open(
                data_dir / filename,
                "r",
                encoding="utf-8",
            ) as file:
                xml_content = file.read()

                data = xmltodict.parse(xml_content)

                return last_seen_at.isoformat(), data

            # async with httpx.AsyncClient() as client:
            #     response = await client.get(
            #         self.settings.PROVIDER1_XML_URL,
            #         timeout=30.0,
            #     )
            #     response.raise_for_status()

            #     data = xmltodict.parse(response.text)
            #     last_seen_at = datetime.now(timezone.utc).isoformat()

            #     return last_seen_at, data

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP request failed: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch raw data from Provider 1: {str(e)}")
            raise

    async def transform_data(
        self, last_seen_at: str, raw_data: dict[str, Any]
    ) -> dict[str, UnifiedProduct]:
        """
        Transform Supplier Provider 1's native format to unified format

        Args:
            last_seen_at: The timestamp when this supplier snapshot was fetched
            raw_data: Raw data from Supplier Provider 1

        Returns:
            dict[str, UnifiedProduct]: Transformed products where key is parent SKU
        """

        conversion_map: dict[
            str, str
        ] = await self.country_mapping_repo.map_name_to_iso()

        unified_products: dict[str, UnifiedProduct] = {}

        products = raw_data.get("products", {}).get("product", [])

        for product in products:
            try:
                valid_product = True

                product_title: str = product.get("title")
                if not product_title:
                    raise ValueError("Product title is required but missing")

                price = float(product.get("prices").get("recommended_retail_price"))
                cost = float(product.get("prices").get("b2b_price"))
                weight = product.get("weight")

                if price <= (cost * 1.09) or price == 0:
                    valid_product = False
                    self.logger.debug(
                        f"{self.name} - Product '{product.get('head_article_number')}' has invalid pricing (price: {price}, cost: {cost}), skipping product"
                    )

                if product.get("country_of_origin"):
                    country_name: str = product.get("country_of_origin")
                    if string_needs_normalization(country_name):
                        country_name = normalize_string(country_name)

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
                        barcode = ",".join(
                            [
                                code
                                for code in barcode_raw
                                if code and code.strip() != ""
                            ]
                        )
                    else:
                        barcode = barcode_raw

                    variant = UnifiedVariant(
                        sku=str(item.get("article_number")),
                        size_title=item.get("size_title"),
                        stock=int(item.get("stock") or 0),
                        price=price,
                        cost=cost,
                        rrp=price,
                        barcode=barcode if barcode is not None else None,
                        weight=int(weight) if weight is not None else None,
                        country_of_origin=country_of_origin,
                        hscode=hscode,
                    )
                    variants.append(variant)

                # Handle images (convert single image to list if necessary)
                media: list[UnifiedMedia] = []
                if product.get("images"):
                    images: str | list[str] | None = product.get("images", {}).get(
                        "image"
                    )

                    if isinstance(images, str):
                        media.append(
                            UnifiedMedia(
                                source_url=images,
                            )
                        )
                    elif isinstance(images, list):
                        images = list(
                            set([img.strip() for img in images if img.strip() != ""])
                        )
                        for image_url in images:
                            media.append(
                                UnifiedMedia(
                                    source_url=image_url,
                                )
                            )

                # Handle categories (convert single category to list if necessary)
                categories: str | None = None
                if product.get("categories", {}).get("category"):
                    categories_raw = product.get("categories", {}).get("category", [])
                    if isinstance(categories_raw, dict):
                        categories_raw: list[dict[str, Any]] = [categories_raw]

                    categories = str(" > ".join([x["title"] for x in categories_raw]))

                # Parse product properties
                properties = await self._transform_product_properties(
                    product, self.name
                )

                # Create unified product
                unified_product = UnifiedProduct(
                    supplier_name=self.name,
                    parent_sku=product.get("head_article_number"),
                    supplier_product_id=product.get("pid"),
                    title=product_title,
                    description=product.get("description"),
                    supplier_category=categories,
                    shopify_category=None,
                    shopify_collections=None,
                    variants=variants,
                    media=media if len(media) > 0 else None,
                    properties=properties,
                    last_seen_at=datetime.fromisoformat(last_seen_at),
                )

                if valid_product:
                    unified_products[product.get("head_article_number")] = (
                        unified_product
                    )

            except Exception as e:
                self.logger.error(
                    f"{self.name} - Transformation failed for product '{product.get('head_article_number')}': {str(e)}"
                )
                # self.logger.exception(str(e))
                # break

        return unified_products

    async def _transform_product_properties(
        self, product: dict[str, Any], supplier_name: Optional[str] = None
    ) -> list[UnifiedPropertyDefinition]:
        """
        Transform product properties from Provider 1's native format to unified format

        Args:
            product: Product data in Provider 1's native format

        Returns:
            list[UnifiedPropertyDefinition]: List of unified property definitions
        """
        values_not_units: list[str | None] = [None, "Enkel", "Multi"]

        product_properties: dict[str, UnifiedPropertyDefinition] = {}

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
                        property_title = properties_ccv_keys[ccv_key]

                        filtered_values = [
                            x.strip()
                            for x in str(product.get(ccv_key)).split("\n")
                            if x.strip() != ""
                        ]
                        filtered_values = [
                            (x[2:] if x[:2] == "- " else x) for x in filtered_values
                        ]
                        filtered_values = [
                            str(regex(x, "str")) for x in filtered_values if x != ""
                        ]

                        product_properties[property_title] = UnifiedPropertyDefinition(
                            key=slugify(property_title, separator="_"),
                            label=property_title,
                            input_kind="multi",
                            storage_kind="metafield_only",
                            value_type="text",
                            created_by="supplier",
                            created_by_supplier_name=supplier_name,
                            values=[
                                UnifiedPropertyValue(
                                    normalized_value=normalize_string(value),
                                    display_value=value,
                                    created_by="supplier",
                                )
                                for value in filtered_values
                            ],
                        )

                case "content":
                    if (
                        product.get(ccv_key) is not None
                        and product.get("content_unit") is not None
                        and product.get("content_unit") != "n.v.t."
                    ):
                        property_title = properties_ccv_keys[ccv_key]

                        value = (
                            str(regex(str(product.get(ccv_key)), "num"))
                            + " "
                            + str(product.get("content_unit"))
                        )

                        product_properties[property_title] = UnifiedPropertyDefinition(
                            key=slugify(property_title, separator="_"),
                            label=property_title,
                            input_kind="single",
                            storage_kind="metaobject_linked",
                            value_type="text",
                            created_by="supplier",
                            created_by_supplier_name=supplier_name,
                            values=[
                                UnifiedPropertyValue(
                                    normalized_value=normalize_string(value),
                                    display_value=value,
                                    created_by="supplier",
                                )
                            ],
                        )

                case "brand":
                    property_title = properties_ccv_keys[ccv_key]

                    value = str(
                        regex(
                            product.get(ccv_key, {}).get("title") or "Merkloos", "str"
                        )
                    )

                    product_properties[property_title] = UnifiedPropertyDefinition(
                        key=slugify(property_title, separator="_"),
                        label=property_title,
                        input_kind="single",
                        storage_kind="metaobject_linked",
                        value_type="text",
                        created_by="supplier",
                        created_by_supplier_name=supplier_name,
                        values=[
                            UnifiedPropertyValue(
                                normalized_value=normalize_string(value),
                                display_value=value,
                                created_by="supplier",
                            )
                        ],
                    )

                case "popularity":
                    property_title = properties_ccv_keys[ccv_key]

                    allowed_values = ["1", "2", "3", "4"]
                    if product.get(ccv_key) in allowed_values:
                        value = str(product.get(ccv_key))
                    else:
                        value = "1"

                    product_properties[property_title] = UnifiedPropertyDefinition(
                        key=slugify(property_title, separator="_"),
                        label=property_title,
                        input_kind="single",
                        storage_kind="metaobject_linked",
                        value_type="text",
                        allow_ai_create_values=False,
                        created_by="supplier",
                        created_by_supplier_name=supplier_name,
                        values=[
                            UnifiedPropertyValue(
                                normalized_value=normalize_string(value),
                                display_value=value,
                                created_by="supplier",
                            )
                        ],
                    )

                case "materials":
                    if product.get(ccv_key) is not None:
                        property_title = properties_ccv_keys[ccv_key]

                        if not isinstance(product[ccv_key]["material"], list):
                            product[ccv_key]["material"] = [
                                product[ccv_key]["material"]
                            ]

                        values: list[str] = [
                            str(regex(value["name"], "str"))
                            for value in product[ccv_key]["material"]
                        ]

                        product_properties[property_title] = UnifiedPropertyDefinition(
                            key=slugify(property_title, separator="_"),
                            label=property_title,
                            input_kind="multi",
                            storage_kind="metaobject_linked",
                            value_type="text",
                            created_by="supplier",
                            created_by_supplier_name=supplier_name,
                            values=[
                                UnifiedPropertyValue(
                                    normalized_value=normalize_string(value),
                                    display_value=value,
                                    created_by="supplier",
                                )
                                for value in values
                            ],
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

                    if isinstance(property_values, list):
                        list_of_values: list[UnifiedPropertyValue] = [
                            UnifiedPropertyValue(
                                normalized_value=normalize_string(value),
                                display_value=value,
                                created_by="supplier",
                            )
                            for value in property_values
                            if value != ""
                        ]
                    else:
                        list_of_values: list[UnifiedPropertyValue] = [
                            UnifiedPropertyValue(
                                normalized_value=normalize_string(property_values),
                                display_value=property_values,
                                created_by="supplier",
                            )
                        ]

                    # Only add property if it has values (not empty string or empty list)
                    if property_values != "" and property_values != [""]:
                        product_properties[property_title] = UnifiedPropertyDefinition(
                            key=slugify(property_title, separator="_"),
                            label=property_title,
                            input_kind=property_single_or_multi,
                            storage_kind="metaobject_linked",
                            value_type="text",
                            created_by="supplier",
                            created_by_supplier_name=supplier_name,
                            values=list_of_values,
                        )

                except Exception as e:
                    self.logger.error(
                        f"Supplier_OneDC - Failed to transform property '{raw_property.get('title')}' for product '{product.get('head_article_number')}': {str(e)}"
                    )

        return [prop for prop in product_properties.values()]
