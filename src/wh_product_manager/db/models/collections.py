from sqlalchemy import BigInteger, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.models.base import Base
from wh_product_manager.db.session_utils import session_scope


class Collections(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    breadcrumbs: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    shopify_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    handle: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    level: Mapped[int] = mapped_column(BigInteger, nullable=False)


class CollectionsRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_all(self) -> dict[str, dict[str, str | int | None]]:
        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(
                    Collections.breadcrumbs,
                    Collections.name,
                    Collections.shopify_category,
                    Collections.collection_id,
                    Collections.handle,
                    Collections.level,
                )
            )
            return {
                breadcrumbs: {
                    "name": name,
                    "shopify_category": shopify_category,
                    "collection_id": collection_id,
                    "handle": handle,
                    "level": level,
                }
                for (
                    breadcrumbs,
                    name,
                    shopify_category,
                    collection_id,
                    handle,
                    level,
                ) in res.all()
            }

    async def save_all(self, data: dict[str, dict[str, str | int | None]]) -> None:
        async with session_scope(self._session_factory) as session:
            for breadcrumbs, details in data.items():
                collection = await session.execute(
                    select(Collections).where(Collections.breadcrumbs == breadcrumbs)
                )
                collection = collection.scalar_one_or_none()
                if collection:
                    collection.name = details["name"]  # type: ignore
                    collection.shopify_category = details["shopify_category"]  # type: ignore
                    collection.collection_id = details["collection_id"]  # type: ignore
                    collection.handle = details["handle"]  # type: ignore
                    collection.level = details["level"]  # type: ignore
                else:
                    new_collection = Collections(
                        breadcrumbs=breadcrumbs,
                        name=details["name"],
                        shopify_category=details["shopify_category"],
                        collection_id=details["collection_id"],
                        handle=details["handle"],
                        level=details["level"],
                    )
                    session.add(new_collection)
