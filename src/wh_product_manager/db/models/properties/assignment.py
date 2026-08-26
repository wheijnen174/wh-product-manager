from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wh_product_manager.db.base_model import Base

if TYPE_CHECKING:
    from wh_product_manager.db.models.products.product import ProductORM
    from wh_product_manager.db.models.properties.definition import PropertyDefinitionORM
    from wh_product_manager.db.models.properties.value import PropertyValueORM

allowed_sources = ("supplier", "generated", "manual")
allowed_assigned_by = ("supplier_feed", "ai_agent", "manual", "system")


class ProductPropertyAssignmentORM(Base):
    __tablename__ = "products_property_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_definition_id: Mapped[int] = mapped_column(
        ForeignKey("property_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_value_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("property_values.id", ondelete="SET NULL"),
        index=True,
    )

    raw_value: Mapped[Optional[str]] = mapped_column(Text)

    source: Mapped[str] = mapped_column(
        Enum(
            *allowed_sources,
            name="property_assignment_source_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    assigned_by: Mapped[str] = mapped_column(
        Enum(
            *allowed_assigned_by,
            name="property_assignment_assigned_by_enum",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["ProductORM"] = relationship()
    definition: Mapped["PropertyDefinitionORM"] = relationship()
    value: Mapped[Optional["PropertyValueORM"]] = relationship()

    __table_args__ = (
        Index(
            "ix_property_assignments_product_definition",
            "product_id",
            "property_definition_id",
        ),
    )
