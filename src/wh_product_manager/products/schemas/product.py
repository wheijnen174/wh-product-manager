from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from wh_product_manager.db.models.products.description import DescriptionORM
from wh_product_manager.db.models.products.product import ProductORM
from wh_product_manager.db.models.products.text_field import TextFieldORM
from wh_product_manager.products.schemas.media import UnifiedMedia
from wh_product_manager.products.schemas.variant import UnifiedVariant
from wh_product_manager.properties.schemas.definition import UnifiedPropertyDefinition
from wh_product_manager.utils.validators import validate_variant_size_titles


@dataclass
class UnifiedProduct:
    """Standard product structure across all suppliers"""

    supplier_name: str
    parent_sku: str
    supplier_product_id: int
    title: str
    description: str
    supplier_category: Optional[str]
    shopify_category: Optional[str]
    shopify_collections: Optional[list[str]]
    variants: list[UnifiedVariant]
    media: Optional[list[UnifiedMedia]]
    properties: Optional[list[UnifiedPropertyDefinition]]
    last_seen_at: Optional[datetime]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "supplier_name": self.supplier_name,
            "parent_sku": self.parent_sku,
            "supplier_product_id": self.supplier_product_id,
            "title": self.title,
            "description": self.description,
            "supplier_category": self.supplier_category,
            "shopify_category": self.shopify_category,
            "shopify_collections": self.shopify_collections,
            "variants": [v.to_dict() for v in self.variants],
            "media": [v.to_dict() for v in (self.media or [])],
            "properties": [
                definition.to_dict() for definition in (self.properties or [])
            ],
            "last_seen_at": self.last_seen_at.isoformat()
            if self.last_seen_at
            else None,
        }

    def to_orm(self) -> ProductORM:
        validate_variant_size_titles(self.variants, product_label=self.parent_sku)

        last_seen_at = self.last_seen_at or datetime.now(timezone.utc)

        product = ProductORM(
            supplier_name=self.supplier_name,
            parent_sku=self.parent_sku,
            supplier_product_id=self.supplier_product_id,
            last_seen_at=last_seen_at,
            missing_since=None,
            is_missing=False,
        )

        if self.description and self.description.strip() != "":
            product.description = [
                DescriptionORM(
                    source="supplier",
                    value=self.description,
                )
            ]

        text_fields: list[TextFieldORM] = []

        text_fields.append(
            TextFieldORM(
                field_name="title",
                source="supplier",
                value=self.title,
            )
        )
        text_fields.append(
            TextFieldORM(
                field_name="supplier_category",
                source="supplier",
                value=self.supplier_category,
            )
        )

        if self.shopify_category:
            text_fields.append(
                TextFieldORM(
                    field_name="shopify_category",
                    source="supplier",
                    value=self.shopify_category,
                )
            )

        if self.shopify_collections:
            text_fields.append(
                TextFieldORM(
                    field_name="shopify_collections",
                    source="supplier",
                    value=",".join(self.shopify_collections),
                )
            )

        product.text_fields = text_fields

        product.variants = [
            variant.to_orm(
                supplier_name=self.supplier_name,
                seen_at=last_seen_at,
            )
            for variant in self.variants
        ]

        product.media = [media.to_orm() for media in (self.media or [])]

        return product
