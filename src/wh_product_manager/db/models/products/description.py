from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wh_product_manager.db.base_model import Base
from wh_product_manager.db.models.products.product import allowed_sources

if TYPE_CHECKING:
    from wh_product_manager.db.models.products.product import ProductORM


class DescriptionORM(Base):
    __tablename__ = "products_descriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        Enum(
            *allowed_sources,
            name="products_description_source_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            length=20,
        ),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(LONGTEXT, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["ProductORM"] = relationship(back_populates="description")

    __table_args__ = (
        # Ensure one entry per product_id + source
        UniqueConstraint("product_id", "source", name="uix_product_description_source"),
        Index("ix_description_source", "source"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "source": self.source,
            "value": self.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
