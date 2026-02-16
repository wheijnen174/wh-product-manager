"""
Unified supplier data schemas
Standard format for all supplier data
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from slugify import slugify


@dataclass
class UnifiedVariant:
    """Standard variant structure across all suppliers"""

    sku: str
    stock: int
    price: float
    cost: float
    barcode: str | None = None
    size_title: str | None = None
    weight: int | None = None
    country_of_origin: str | None = None
    hscode: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sku": self.sku,
            "stock": self.stock,
            "price": self.price,
            "cost": self.cost,
            "barcode": self.barcode,
            "size_title": self.size_title,
            "weight": self.weight,
            "country_of_origin": self.country_of_origin,
            "hscode": self.hscode,
        }

    def graphql_variable__create(
        self, update_time: str, location_id: str
    ) -> dict[str, Any]:
        """Format variant data for Shopify GraphQL product creation"""
        if self.size_title is not None:
            option_values = [
                {
                    "optionName": "Maat",
                    "linkedMetafieldValue": self.size_title,
                }
            ]
        else:
            option_values = [
                {
                    "optionName": "Title",
                    "name": "Default Title",
                }
            ]

        return {
            "barcode": self.barcode,
            "inventoryItem": {
                "cost": self.cost,
                "countryCodeOfOrigin": self.country_of_origin,
                "harmonizedSystemCode": str(self.hscode)
                if self.hscode is not None
                else None,
                "measurement": {
                    "weight": {
                        "unit": "GRAMS",
                        "value": float(self.weight) if self.weight is not None else 0.0,
                    },
                },
                "requiresShipping": True,
                "sku": self.sku,
                "tracked": True,
            },
            "inventoryPolicy": "DENY",
            "inventoryQuantities": {
                "locationId": location_id,
                "name": "available",
                "quantity": self.stock,
            },
            "metafields": [
                {
                    "namespace": "whpm",
                    "key": "update_time",
                    "value": update_time,
                },
            ],
            "optionValues": option_values,
            "price": self.price,
            "sku": self.sku,
            "taxable": True,
        }

    def graphql_variable__update(self) -> dict[str, Any]:
        """Format variant data for Shopify GraphQL product update"""
        return {"Test": "Update"}


@dataclass
class UnifiedProperty:
    """Standard product property structure across all suppliers"""

    single_or_multi: str  # "single" or "multi"
    field_type: str  # "metaobject" or "metafield"
    values: list[str] | str

    def __post_init__(self) -> None:
        """Validate the property after initialization"""
        # Validate single_or_multi
        if self.single_or_multi not in ("single", "multi"):
            raise ValueError(
                f"single_or_multi must be 'single' or 'multi', "
                f"got '{self.single_or_multi}'"
            )

        # Validate field_type
        if self.field_type not in ("metaobject", "metafield"):
            raise ValueError(
                f"field_type must be 'metaobject' or 'metafield', "
                f"got '{self.field_type}'"
            )

        # Validate values based on single_or_multi
        if self.single_or_multi == "multi":
            if isinstance(self.values, str):
                # If it's a string, convert it to a list
                self.values = [self.values]
            elif not isinstance(self.values, list):  # type: ignore
                raise ValueError(
                    f"When single_or_multi='multi', values must be a list, "
                    f"got {type(self.values).__name__}"
                )
            if not all(isinstance(v, str) for v in self.values):  # type: ignore
                raise ValueError("All values in the list must be strings")
        else:  # single_or_multi == "single"
            if not isinstance(self.values, str):
                raise ValueError(
                    f"When single_or_multi='single', values must be a string, "
                    f"got {type(self.values).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "single_or_multi": self.single_or_multi,
            "field_type": self.field_type,
            "values": self.values,
        }

    def graphql_variable__create(self) -> dict[str, Any]:
        """Format property data for Shopify GraphQL product creation"""
        print(json.dumps(self.to_dict(), indent=2))
        print("\n\n\n")

        return {"Test": "Create"}

    def graphql_variable__update(self) -> dict[str, Any]:
        """Format property data for Shopify GraphQL product update"""
        return {"Test": "Update"}


@dataclass
class UnifiedProduct:
    """Standard product structure across all suppliers"""

    supplier_product_id: int
    title: str
    variants: list[UnifiedVariant]
    images: list[str] | None = None
    category: str | None = None
    description: str | None = None
    properties: dict[str, UnifiedProperty] | None = None
    extra_data: dict[str, Any] = field(default_factory=lambda: {})

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "supplier_product_id": self.supplier_product_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "images": self.images,
            "variants": [v.to_dict() for v in self.variants],
            "properties": {k: v.to_dict() for k, v in (self.properties or {}).items()},
            "extra_data": self.extra_data,
        }

    def graphql_variable__create(self) -> dict[str, Any]:
        """Format product data for Shopify GraphQL product creation"""
        if self.extra_data.get("parent_sku") is None:
            raise TypeError(
                "'parent_sku' must be set to 'extra_data' for GraphQL product creation"
            )
        if self.extra_data.get("update_time") is None:
            self.extra_data["update_time"] = datetime.now(timezone.utc).isoformat()
        if self.extra_data.get("supplier_name") is None:
            raise TypeError(
                "'supplier_name' must be set to 'extra_data' for GraphQL product creation"
            )

        category = self.extra_data.get("shopify_category", None)
        category = "gid://shopify/TaxonomyCategory/" + category if category else None

        collections_to_join = self.extra_data.get("shopify_collections", [])

        product_options: list[Any] = self.extra_data.get("product_options", [])
        if len(product_options) > 1 and None in product_options:
            raise ValueError(
                "'size_title' values must be set to all variants if there are multiple options"
            )
        elif len(product_options) > 0 and None not in product_options:
            print(json.dumps(product_options, indent=2))
            product_options = [
                {
                    "name": "Maat",
                    "linkedMetafield": {
                        "namespace": "product",
                        "key": "product_size",
                        "values": [
                            "gid://shopify/Metaobject/494892187992",
                            "gid://shopify/Metaobject/494892220760",
                        ],
                    },
                }
            ]
            print(json.dumps(product_options, indent=2))
        else:
            product_options = [None]

        return {
            "media": [
                {
                    "alt": self.title + " - " + str(i + 1),
                    "mediaContentType": "IMAGE",
                    "originalSource": url,
                }
                for i, url in enumerate(self.images or [])
            ],
            "product": {
                "title": self.title,
                "descriptionHtml": self.description or "",
                "handle": slugify(self.title + "-" + str(self.supplier_product_id)),
                "category": category,
                "collectionsToJoin": collections_to_join,
                "productOptions": product_options
                if product_options != [None]
                else None,
                "vendor": self.extra_data.get("supplier_name"),
                "metafields": [
                    {
                        "namespace": "whpm",
                        "key": "head_article_number",
                        "value": self.extra_data.get("parent_sku"),
                    },
                    {
                        "namespace": "whpm",
                        "key": "update_time",
                        "value": self.extra_data.get("update_time"),
                    },
                    {
                        "namespace": "whpm",
                        "key": "number_of_sales",
                        "value": "0",
                    },
                ],
            },
        }

    def graphql_variable__update(self) -> dict[str, Any]:
        """Format product data for Shopify GraphQL product update"""
        return {"Test": "Update"}

    def graphql_variable__create_set(self, location_id: str) -> dict[str, Any]:
        """Format product data for Shopify GraphQL product creation of product set (parent + variant)"""
        if self.extra_data.get("parent_sku") is None:
            raise TypeError(
                "'parent_sku' must be set to 'extra_data' for GraphQL product creation"
            )

        if self.extra_data.get("update_time") is not None:
            update_time: str = str(self.extra_data.get("update_time"))
        else:
            update_time: str = datetime.now(timezone.utc).isoformat()

        if self.extra_data.get("supplier_name") is None:
            raise TypeError(
                "'supplier_name' must be set to 'extra_data' for GraphQL product creation"
            )

        category = self.extra_data.get("shopify_category", None)
        category = "gid://shopify/TaxonomyCategory/" + category if category else None

        collections_to_join = self.extra_data.get("shopify_collections", [])

        media = [
            {
                "alt": self.title + " - " + str(i + 1),
                "contentType": "IMAGE",
                "filename": slugify(self.title + " - " + str(i + 1).zfill(2))
                + Path(urlparse(url).path).suffix,
                "originalSource": urlparse(url).geturl(),
            }
            for i, url in enumerate(self.images or [])
        ]

        product_options: list[Any] = [
            var.size_title for var in self.variants if var.size_title is not None
        ]
        if len(product_options) > 0 and None in product_options:
            raise ValueError(
                "'size_title' values must be set to all variants if there are multiple options"
            )
        elif len(product_options) > 0 and None not in product_options:
            product_options = [
                {
                    "name": "Maat",
                    "linkedMetafield": {
                        "namespace": "product",
                        "key": "maat",
                        "values": product_options,
                    },
                }
            ]
        else:
            product_options = [{"name": "Title", "values": [{"name": "Default Title"}]}]

        metafields: list[dict[str, Any]] = [
            {
                "namespace": "whpm",
                "key": "head_article_number",
                "value": self.extra_data.get("parent_sku"),
            },
            {
                "namespace": "whpm",
                "key": "update_time",
                "value": update_time,
            },
            {
                "namespace": "whpm",
                "key": "number_of_sales",
                "value": "0",
            },
        ]

        # Process properties into metafields/metaobjects based on their configuration
        processed_properties: dict[str, Any] = self.extra_data.get(
            "processed_properties", {}
        )
        metafields += [
            {
                "namespace": name.split(".")[0],
                "key": ".".join(name.split(".")[1:]),
                "value": json.dumps(values) if isinstance(values, list) else values,
            }
            for name, values in processed_properties.items()
        ]

        tags = ["Nieuw"]

        if (
            self.properties is not None
            and self.properties.get("Populariteit", "1") == "4"
        ):
            tags.append("Populair")

        variants = [
            var.graphql_variable__create(update_time, location_id)
            for var in self.variants
        ]

        return {
            "synchronous": True,
            "productSet": {
                "title": self.title,
                "handle": slugify(self.title + "-" + str(self.supplier_product_id)),
                "descriptionHtml": self.description or "",
                "vendor": self.extra_data.get("supplier_name"),
                "category": category,
                "collections": collections_to_join,
                "files": media,
                "metafields": metafields,
                "productOptions": product_options,
                "tags": tags,
                "variants": variants,
            },
        }


@dataclass
class SupplierDataResult:
    """Result of fetching and transforming supplier data"""

    supplier_name: str
    status: str  # "success" or "failed"
    item_count: int = 0
    error: str | None = None
    products: dict[str, UnifiedProduct] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "supplier_name": self.supplier_name,
            "status": self.status,
            "item_count": self.item_count,
            "error": self.error,
            "products": {k: v.to_dict() for k, v in (self.products or {}).items()},
        }
