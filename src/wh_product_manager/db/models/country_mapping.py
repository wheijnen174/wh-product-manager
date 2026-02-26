from sqlalchemy import BigInteger, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.models.base import Base


class CountryMapping(Base):
    __tablename__ = "country_mapping"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("country_code", "language", name="uq_country_code_language"),
        Index("idx_country_code_language", "country_code"),
    )
