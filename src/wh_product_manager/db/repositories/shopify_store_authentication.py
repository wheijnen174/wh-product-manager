from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.shopify.store_authentication import (
    ShopifyStoreAuthentication,
)
from wh_product_manager.db.session_utils import session_scope


class ShopifyStoreAuthenticationRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], logger: Logger
    ):
        self._session_factory = session_factory
        self.logger = logger

    async def get_store_by_id(self, store_id: int) -> ShopifyStoreAuthentication:
        async with session_scope(self._session_factory) as session:
            stmt = select(ShopifyStoreAuthentication).where(
                ShopifyStoreAuthentication.id == store_id
            )
            result = await session.execute(stmt)
            store = result.scalar_one_or_none()

            if store is None:
                raise ValueError(f"No store found for store_id: {store_id}")

            return store

    async def get_access_token(self, store_id: str) -> tuple[str, str]:
        async with session_scope(self._session_factory) as session:
            stmt = select(
                ShopifyStoreAuthentication.access_token,
                ShopifyStoreAuthentication.token_encryption_key,
            ).where(ShopifyStoreAuthentication.store_id == store_id)
            result = await session.execute(stmt)
            row = result.one_or_none()

            if row is None:
                raise ValueError(
                    f"No authentication data found for store_id: {store_id}"
                )

            access_token, token_encryption_key = row
            return access_token, token_encryption_key

    async def get_api_version(self, store_id: str) -> str:
        async with session_scope(self._session_factory) as session:
            stmt = select(
                ShopifyStoreAuthentication.api_version,
            ).where(ShopifyStoreAuthentication.store_id == store_id)
            result = await session.execute(stmt)
            row = result.one_or_none()

            if row is None:
                raise ValueError(
                    f"No authentication data found for store_id: {store_id}"
                )

            api_version = row[0]
            return api_version

    async def get_api_batch_delay(self, store_id: str) -> str:
        async with session_scope(self._session_factory) as session:
            stmt = select(
                ShopifyStoreAuthentication.api_batch_delay,
            ).where(ShopifyStoreAuthentication.store_id == store_id)
            result = await session.execute(stmt)
            row = result.one_or_none()

            if row is None:
                raise ValueError(
                    f"No authentication data found for store_id: {store_id}"
                )

            api_batch_delay = row[0]
            return api_batch_delay

    async def get_stores(self) -> dict[int, dict[str, Any]]:
        async with session_scope(self._session_factory) as session:
            stmt = select(ShopifyStoreAuthentication)
            result = await session.execute(stmt)
            stores = result.scalars().unique().all()

            return {
                store.id: {
                    "store_id": store.store_id,
                    "api_version": store.api_version,
                    "api_batch_delay": store.api_batch_delay,
                }
                for store in (stores or [])
            }

    async def get_store_by_name(self, store_name: str) -> dict[str, Any] | None:
        async with session_scope(self._session_factory) as session:
            stmt = select(ShopifyStoreAuthentication).where(
                ShopifyStoreAuthentication.store_id == store_name
            )
            result = await session.execute(stmt)
            store = result.one_or_none()

            if store is None:
                return None

            return {
                "store_id": store[0].id,
                "store_name": store[0].store_id,
                "api_version": store[0].api_version,
                "api_batch_delay": store[0].api_batch_delay,
            }
