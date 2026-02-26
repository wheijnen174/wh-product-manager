from sqlalchemy import BigInteger, Index, String, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.models.base import Base
from wh_product_manager.db.session_utils import session_scope
from wh_product_manager.utils.formatters import normalize_string


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


class CountryMappingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def map_name_to_iso(self) -> dict[str, str]:
        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(CountryMapping.name, CountryMapping.country_code)
            )
            conversion_map = {
                name.lower(): country_code for (name, country_code) in res.all()
            }

        prepared_map: dict[str, str] = {}

        for name, code in conversion_map.items():
            if name.lower() not in prepared_map.keys():
                prepared_map[name.lower()] = code.lower()

            normalized_name = normalize_string(name.lower()).lower()
            if (
                normalized_name != name.lower()
                and normalized_name not in prepared_map.keys()
            ):
                prepared_map[normalized_name] = code.lower()

        return prepared_map
