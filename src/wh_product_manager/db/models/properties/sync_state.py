from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.base_model import Base


class PropertySyncStateORM(Base):
    __tablename__ = "property_sync_state"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    entity_type: Mapped[str] = mapped_column(
        Enum(
            "definition",
            "value",
            "assignment",
            name="property_sync_entity_type_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    target: Mapped[str] = mapped_column(
        Enum(
            "shopify_metafield_definition",
            "shopify_metaobject_definition",
            "shopify_metaobject_value",
            "shopify_product_assignment",
            name="property_sync_target_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "in_progress",
            "succeeded",
            "failed",
            "dead_letter",
            name="property_sync_status_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "target",
            name="uq_property_sync_state_entity_target",
        ),
        Index("ix_property_sync_state_due", "status", "next_retry_at"),
    )
