from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
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
    from wh_product_manager.db.models.properties.value import PropertyValueORM

# Allowed values for Enum fields
allowed_input_kind = (
    "single",
    "multi",
)
allowed_storage_kind = (
    "metafield_only",
    "metaobject_linked",
)
allowed_value_type = (
    "text",
    "number",
    "boolean",
    "json",
)
allowed_created_by = (
    "supplier",
    "ai",
    "manual",
    "system",
    "shopify",
)


class PropertyDefinitionORM(Base):
    __tablename__ = "property_definitions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    key: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    input_kind: Mapped[str] = mapped_column(
        Enum(
            *allowed_input_kind,
            name="property_definition_input_kind_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    storage_kind: Mapped[str] = mapped_column(
        Enum(
            *allowed_storage_kind,
            name="property_definition_storage_kind_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    value_type: Mapped[str] = mapped_column(
        Enum(
            *allowed_value_type,
            name="property_definition_value_type_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default="text",
    )

    allow_supplier_create: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_ai_assign: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_ai_create_values: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_by: Mapped[str] = mapped_column(
        Enum(
            *allowed_created_by,
            name="property_definition_created_by_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default="system",
    )
    created_by_supplier_name: Mapped[Optional[str]] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    values: Mapped[list["PropertyValueORM"]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )

    shopify_assignments: Mapped[list["ShopifyObjectAssignmentORM"]] = relationship(
        "ShopifyObjectAssignmentORM",
        primaryjoin=lambda: and_(
            PropertyDefinitionORM.id
            == foreign(ShopifyObjectAssignmentORM.local_object_id),
            ShopifyObjectAssignmentORM.local_object_type == "property_definition",
        ),
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint("key", name="uq_property_definitions_key"),
        Index("ix_property_definitions_storage_kind", "storage_kind"),
        Index(
            "ix_property_definitions_created_by_supplier", "created_by_supplier_name"
        ),
    )
