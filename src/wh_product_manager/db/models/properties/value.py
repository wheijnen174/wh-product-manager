from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
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
    from wh_product_manager.db.models.properties.definition import PropertyDefinitionORM

allowed_created_by = ("supplier", "ai", "manual", "system", "shopify")


class PropertyValueORM(Base):
    __tablename__ = "property_values"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    property_definition_id: Mapped[int] = mapped_column(
        ForeignKey("property_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    display_value: Mapped[str] = mapped_column(String(255), nullable=False)

    created_by: Mapped[str] = mapped_column(
        Enum(
            *allowed_created_by,
            name="property_value_created_by_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default="system",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    definition: Mapped["PropertyDefinitionORM"] = relationship(back_populates="values")

    shopify_assignments: Mapped[list["ShopifyObjectAssignmentORM"]] = relationship(
        "ShopifyObjectAssignmentORM",
        primaryjoin=lambda: and_(
            PropertyValueORM.id == foreign(ShopifyObjectAssignmentORM.local_object_id),
            ShopifyObjectAssignmentORM.local_object_type == "property_value",
        ),
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "property_definition_id",
            "normalized_value",
            name="uq_property_values_definition_normalized",
        ),
        Index(
            "ix_property_values_definition_display",
            "property_definition_id",
            "display_value",
        ),
    )
