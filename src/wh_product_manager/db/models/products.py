from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wh_product_manager.db.models.base import Base


# Define 'products' table
class Products(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_sku: Mapped[str] = mapped_column(String(255), nullable=False)

    supplier_product_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # TODO: Optional fields

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ORM relationship
    texts: Mapped[list["ProductsTexts"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("supplier_name", "parent_sku", name="uq_supplier_parent_sku"),
        Index("ix_products_supplier", "supplier_name"),
        Index("ix_products_parent_sku", "parent_sku"),
    )


# Define 'products_texts' table
class ProductsTexts(Base):
    __tablename__ = "products_texts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    field: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)

    text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    product: Mapped[Products] = relationship(back_populates="texts")

    __table_args__ = (
        # One row per:
        # product + field + source + language
        UniqueConstraint(
            "product_id",
            "field",
            "source",
            "language",
            name="uq_product_field_source_language",
        ),
        Index("ix_products_texts_lookup", "product_id", "field", "source", "language"),
        Index("ix_products_texts_field", "field"),
    )
