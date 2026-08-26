from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
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
    from wh_product_manager.db.models.products.product import ProductORM


class VariantORM(Base):
    __tablename__ = "products_variants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    supplier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    size_title: Mapped[Optional[str]] = mapped_column(String(50))
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    rrp: Mapped[Optional[float]] = mapped_column(Float)
    barcode: Mapped[Optional[str]] = mapped_column(String(100))
    weight: Mapped[Optional[int]] = mapped_column(Integer)
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(2))
    hscode: Mapped[Optional[int]] = mapped_column(BigInteger)

    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    missing_since: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_missing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Table: Shopify assignments
    shopify_assignments: Mapped[list["ShopifyObjectAssignmentORM"]] = relationship(
        "ShopifyObjectAssignmentORM",
        primaryjoin=lambda: and_(
            VariantORM.id == foreign(ShopifyObjectAssignmentORM.local_object_id),
            ShopifyObjectAssignmentORM.local_object_type == "variant",
        ),
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "supplier_name",
            "sku",
            name="uq_variants_supplier_sku",
        ),
        Index("ix_variants_supplier_sku", "supplier_name", "sku"),
    )

    product: Mapped["ProductORM"] = relationship(back_populates="variants")

    def to_dict(self) -> dict[str, Any]:
        shopify_assignments = self._loaded_collection("shopify_assignments")

        return {
            "id": self.id,
            "product_id": self.product_id,
            "supplier_name": self.supplier_name,
            "sku": self.sku,
            "size_title": self.size_title,
            "stock": self.stock,
            "price": self.price,
            "cost": self.cost,
            "rrp": self.rrp,
            "barcode": self.barcode,
            "weight": self.weight,
            "country_of_origin": self.country_of_origin,
            "hscode": self.hscode,
            "last_seen_at": self.last_seen_at,
            "missing_since": self.missing_since,
            "is_missing": self.is_missing,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shopify_assignments": [sa.to_dict() for sa in shopify_assignments],
        }
