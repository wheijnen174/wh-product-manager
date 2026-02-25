""" """

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.models.base import Base


class CountryMapping(Base):
    __tablename__ = "country_mapping"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("country_code", "language", name="uq_country_code_language"),
        Index("idx_country_code_language", "country_code"),
    )
