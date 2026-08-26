from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    event,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from wh_product_manager.db.base_model import Base

allowed_local_object_types = (
    "product",
    "variant",
    "media",
    "property_definition",
    "property_value",
)

allowed_shopify_object_types = (
    "product",
    "product_variant",
    "media_image",
    "metaobject",
    "metafield",
)


class ShopifyObjectAssignmentORM(Base):
    """Generic table mapping local objects to Shopify object IDs per store."""

    __tablename__ = "shopify_object_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    store_id: Mapped[int] = mapped_column(
        ForeignKey("shopify_authorized_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    local_object_type: Mapped[str] = mapped_column(
        Enum(
            *allowed_local_object_types,
            name="shopify_local_object_type_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
    )
    local_object_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    shopify_object_type: Mapped[str] = mapped_column(
        Enum(
            *allowed_shopify_object_types,
            name="shopify_object_type_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
    )
    shopify_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional discriminator when one local object maps to multiple Shopify objects
    # of the same type (for example property metaobject and metafield links).
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # One row per local object -> Shopify object mapping in a store.
        UniqueConstraint(
            "store_id",
            "local_object_type",
            "local_object_id",
            "shopify_object_type",
            "role",
            name="uq_shopify_object_assignments_local_map",
        ),
        Index(
            "ix_shopify_object_assignments_local_lookup",
            "store_id",
            "local_object_type",
            "local_object_id",
        ),
        # Prevent duplicate Shopify IDs inside one store.
        UniqueConstraint(
            "store_id",
            "shopify_id",
            name="uq_shopify_object_assignments_store_shopify_id",
        ),
        Index(
            "ix_shopify_object_assignments_shopify_lookup",
            "store_id",
            "shopify_id",
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "store_id": self.store_id,
            "local_object_type": self.local_object_type,
            "local_object_id": self.local_object_id,
            "shopify_object_type": self.shopify_object_type,
            "shopify_id": self.shopify_id,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@event.listens_for(Session, "before_flush")
def validate_variant_parent_product(
    session: Session, flush_context: Any, instances: Any
) -> None:
    pending_assignments = [
        obj
        for obj in list(session.new) + list(session.dirty)
        if isinstance(obj, ShopifyObjectAssignmentORM)
    ]

    if not pending_assignments:
        return

    pending_product_assignments = {
        (assignment.store_id, assignment.local_object_id)
        for assignment in pending_assignments
        if assignment.local_object_type == "product"
        and assignment.store_id is not None  # type: ignore
        and assignment.local_object_id is not None  # type: ignore
    }

    for assignment in pending_assignments:
        if assignment.local_object_type != "variant":
            continue

        if assignment.store_id is None or assignment.local_object_id is None:  # type: ignore
            raise ValueError(
                "Variant Shopify assignments require store_id and local_object_id."
            )

        from wh_product_manager.db.models.products.variant import VariantORM

        variant_row = session.get(VariantORM, assignment.local_object_id)
        if variant_row is None:
            raise ValueError(
                f"Cannot assign Shopify ID to variant {assignment.local_object_id}: variant does not exist."
            )

        if not variant_row.product_id:
            raise ValueError(
                f"Cannot assign Shopify ID to variant {assignment.local_object_id}: parent product is missing."
            )

        parent_key = (assignment.store_id, variant_row.product_id)
        if parent_key in pending_product_assignments:
            continue

        parent_exists_stmt = select(ShopifyObjectAssignmentORM.id).where(
            ShopifyObjectAssignmentORM.store_id == assignment.store_id,
            ShopifyObjectAssignmentORM.local_object_type == "product",
            ShopifyObjectAssignmentORM.local_object_id == variant_row.product_id,
        )
        parent_exists = session.execute(parent_exists_stmt).scalar_one_or_none()
        if parent_exists is None:
            raise ValueError(
                f"Cannot assign Shopify ID to variant {assignment.local_object_id}: parent product {variant_row.product_id} does not have a Shopify assignment for store {assignment.store_id}."
            )
