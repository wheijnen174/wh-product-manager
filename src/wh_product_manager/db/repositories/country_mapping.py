from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.db.models.country_mapping import CountryMapping
from wh_product_manager.db.session_utils import session_scope
from wh_product_manager.utils.formatters import normalize_string


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
