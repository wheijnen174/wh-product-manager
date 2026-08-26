from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, and_, func
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship, validates
from sqlalchemy.sql import false

from wh_product_manager.db.base_model import Base
from wh_product_manager.db.models.shopify.object_assignments import (
    ShopifyObjectAssignmentORM,
)

if TYPE_CHECKING:
    from wh_product_manager.db.models.products.product import ProductORM


class MediaORM(Base):
    __tablename__ = "products_media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    upload_allowed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )

    filename: Mapped[Optional[str]] = mapped_column(String(255))
    alt_text: Mapped[Optional[str]] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(20))
    source_url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["ProductORM"] = relationship(back_populates="media")

    # Table: Shopify assignments
    shopify_assignments: Mapped[list["ShopifyObjectAssignmentORM"]] = relationship(
        "ShopifyObjectAssignmentORM",
        primaryjoin=lambda: and_(
            MediaORM.id == foreign(ShopifyObjectAssignmentORM.local_object_id),
            ShopifyObjectAssignmentORM.local_object_type == "media",
        ),
        viewonly=True,
    )

    @validates("filename", "alt_text", "content_type", "source_url")
    def _validate_media_fields(self, key: str, value: Optional[str]) -> Optional[str]:
        # Keep upload_allowed derived from required media fields.
        normalized = value.strip() if isinstance(value, str) else value

        field_values: dict[str, Optional[str]] = {
            "filename": self.filename,
            "alt_text": self.alt_text,
            "content_type": self.content_type,
            "source_url": self.source_url,
        }
        field_values[key] = normalized

        self.upload_allowed = all(
            self._has_value(field_values[field_name])
            for field_name in ("filename", "alt_text", "content_type", "source_url")
        )

        return normalized

    @staticmethod
    def _has_value(value: Optional[str]) -> bool:
        return value is not None and value.strip() != ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "upload_allowed": self.upload_allowed,
            "filename": self.filename,
            "alt_text": self.alt_text,
            "content_type": self.content_type,
            "source_url": self.source_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
