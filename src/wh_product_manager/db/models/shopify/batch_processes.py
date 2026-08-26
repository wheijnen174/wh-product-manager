from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.base_model import Base


class ShopifyBatchProcessORM(Base):
    __tablename__ = "shopify_batch_processes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    store_id: Mapped[int] = mapped_column(
        ForeignKey("shopify_authorized_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    shopify_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    operation: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Allowed values: pending, processing, failed, succeeded, dead_letter
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    objects_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    objects_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    query: Mapped[Optional[str]] = mapped_column(LONGTEXT, nullable=True)
    variables: Mapped[JSON] = mapped_column(
        JSON, nullable=False, default={}, server_default="{}"
    )
    result: Mapped[Optional[str]] = mapped_column(LONGTEXT, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "ix_store_id_operation_status",
            "store_id",
            "operation",
            "status",
        ),
    )
