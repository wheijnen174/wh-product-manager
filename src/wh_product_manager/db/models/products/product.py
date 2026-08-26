from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    and_,
    func,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from wh_product_manager.db.base_model import Base
from wh_product_manager.db.models.shopify.object_assignments import (
    ShopifyObjectAssignmentORM,
)

if TYPE_CHECKING:
    from wh_product_manager.db.models.products.description import DescriptionORM
    from wh_product_manager.db.models.products.media import MediaORM
    from wh_product_manager.db.models.products.text_field import TextFieldORM
    from wh_product_manager.db.models.products.variant import VariantORM
    from wh_product_manager.db.models.properties.assignment import (
        ProductPropertyAssignmentORM,
    )

allowed_sources = ("supplier", "generated")
allowed_text_fields = (  # Be sure to update relationship definitions in ProductORM if this is changed!
    "title",
    "supplier_category",
    "shopify_category",
    "shopify_collections",
)


class ProductORM(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    supplier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_sku: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_product_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    model_number: Mapped[Optional[str]] = mapped_column(String(100))

    # Table: Description
    description: Mapped[list["DescriptionORM"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    # Table: Text fields
    text_fields: Mapped[list["TextFieldORM"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    title: Mapped[list["TextFieldORM"]] = relationship(
        "TextFieldORM",
        primaryjoin="and_(ProductORM.id == TextFieldORM.product_id, TextFieldORM.field_name == 'title')",
        viewonly=True,
        uselist=True,
        overlaps="text_fields,product",
    )
    supplier_category: Mapped[list["TextFieldORM"]] = relationship(
        "TextFieldORM",
        primaryjoin="and_(ProductORM.id == TextFieldORM.product_id, TextFieldORM.field_name == 'supplier_category')",
        viewonly=True,
        uselist=True,
        overlaps="text_fields,product",
    )
    shopify_category: Mapped[list["TextFieldORM"]] = relationship(
        "TextFieldORM",
        primaryjoin="and_(ProductORM.id == TextFieldORM.product_id, TextFieldORM.field_name == 'shopify_category')",
        viewonly=True,
        uselist=True,
        overlaps="text_fields,product",
    )
    shopify_collections: Mapped[list["TextFieldORM"]] = relationship(
        "TextFieldORM",
        primaryjoin="and_(ProductORM.id == TextFieldORM.product_id, TextFieldORM.field_name == 'shopify_collections')",
        viewonly=True,
        uselist=True,
        overlaps="text_fields,product",
    )

    # Table: Variants
    variants: Mapped[list["VariantORM"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    # Table: Media
    media: Mapped[list["MediaORM"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    # Table: Property assignments
    property_assignments: Mapped[list["ProductPropertyAssignmentORM"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    # Table: Shopify assignments
    shopify_assignments: Mapped[list["ShopifyObjectAssignmentORM"]] = relationship(
        "ShopifyObjectAssignmentORM",
        primaryjoin=lambda: and_(
            ProductORM.id == foreign(ShopifyObjectAssignmentORM.local_object_id),
            ShopifyObjectAssignmentORM.local_object_type == "product",
        ),
        viewonly=True,
    )

    # Booleans tracking AI processing status
    has_ai_processed_text: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    has_ai_processed_media: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    has_ai_processed_properties: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    is_publishable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Timestamps and status tracking
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    missing_since: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_missing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # One row per:
        # supplier_name + parent_sku
        UniqueConstraint(
            "supplier_name",
            "parent_sku",
            name="uq_products_supplier_sku",
        ),
        Index("ix_products_supplier_sku", "supplier_name", "parent_sku"),
        # One row per:
        # supplier_name + supplier_product_id
        UniqueConstraint(
            "supplier_name",
            "supplier_product_id",
            name="uq_products_supplier_id",
        ),
        Index("ix_products_supplier_id", "supplier_name", "supplier_product_id"),
        # One row per:
        # supplier_name + model_number
        UniqueConstraint(
            "supplier_name",
            "model_number",
            name="uq_products_supplier_model_number",
        ),
        Index("ix_products_supplier_model_number", "supplier_name", "model_number"),
    )

    def to_dict(self) -> dict[str, Any]:
        descriptions = self._loaded_collection("description")
        variants = self._loaded_collection("variants")
        media = self._loaded_collection("media")
        shopify_assignments = self._loaded_collection("shopify_assignments")

        return {
            "id": self.id,
            "supplier_name": self.supplier_name,
            "parent_sku": self.parent_sku,
            "supplier_product_id": self.supplier_product_id,
            "model_number": self.model_number,
            "has_ai_processed_text": self.has_ai_processed_text,
            "has_ai_processed_media": self.has_ai_processed_media,
            "has_ai_processed_properties": self.has_ai_processed_properties,
            "is_publishable": self.is_publishable,
            "last_seen_at": self.last_seen_at,
            "missing_since": self.missing_since,
            "is_missing": self.is_missing,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "title": [tf.to_dict() for tf in self._loaded_collection("title")],
            "supplier_category": [
                tf.to_dict() for tf in self._loaded_collection("supplier_category")
            ],
            "shopify_category": [
                tf.to_dict() for tf in self._loaded_collection("shopify_category")
            ],
            "shopify_collections": [
                tf.to_dict() for tf in self._loaded_collection("shopify_collections")
            ],
            "description": [d.to_dict() for d in descriptions],
            "variants": [v.to_dict() for v in variants],
            "media": [m.to_dict() for m in media],
            "shopify_assignments": [sa.to_dict() for sa in shopify_assignments],
        }
