from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.shopify.category_taxonomies import (
    ShopifyCategoryTaxonomies,
)
from wh_product_manager.db.session_utils import session_scope


class ShopifyCategoryTaxonomiesRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], logger: Logger
    ):
        self._session_factory = session_factory
        self.logger = logger

    async def get_all(self) -> list[str]:
        async with session_scope(self._session_factory) as session:
            res = await session.execute(select(ShopifyCategoryTaxonomies.code))
            codes = [code for (code,) in res.all()]
            self.logger.info(f"Fetched {len(codes)} category taxonomies")
            return codes
