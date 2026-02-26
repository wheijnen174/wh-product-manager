from sqlalchemy import BigInteger, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.models.base import Base
from wh_product_manager.db.session_utils import session_scope
from wh_product_manager.utils.data_loader import load_json


class ShopifyCategoryTaxonomies(Base):
    __tablename__ = "shopify_category_taxonomies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class ShopifyCategoryTaxonomiesRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_all(self) -> list[str]:
        async with session_scope(self._session_factory) as session:
            res = await session.execute(select(ShopifyCategoryTaxonomies.code))
            return [code for (code,) in res.all()]

    async def temp_feed(self) -> None:
        """
        Temporary method to feed the database with category taxonomies
        """
        taxonomies = load_json("shopify_category_taxonomies.json")

        async with session_scope(self._session_factory) as session:
            for code in taxonomies:
                existing = await session.execute(
                    select(ShopifyCategoryTaxonomies).where(
                        ShopifyCategoryTaxonomies.code == code
                    )
                )
                if not existing.scalars().first():
                    session.add(ShopifyCategoryTaxonomies(code=code))
            await session.commit()
