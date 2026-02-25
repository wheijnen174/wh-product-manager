from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from wh_product_manager.db.session_utils import session_scope

from wh_product_manager.db.models.country_mapping import CountryMapping


class CountryMappingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def count(self) -> int:
        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(func.count()).select_from(CountryMapping)
            )
            return int(res.scalar_one())

    async def get_name(self, country_code: str, language: str) -> str | None:
        cc = country_code.strip().upper()
        lang = language.strip().lower()

        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(CountryMapping.name).where(
                    CountryMapping.country_code == cc,
                    CountryMapping.language == lang,
                )
            )
            return res.scalar_one_or_none()

    async def get_all_for_country(self, country_code: str) -> dict[str, str]:
        cc = country_code.strip().upper()

        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(CountryMapping.language, CountryMapping.name).where(
                    CountryMapping.country_code == cc
                )
            )
            return {language: name for (language, name) in res.all()}
