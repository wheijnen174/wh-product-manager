from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.shopify.batch_processes import (
    ShopifyBatchProcessORM,
)
from wh_product_manager.db.session_utils import session_scope


class ShopifyBatchProcessesRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], logger: Logger
    ):
        self._session_factory = session_factory
        self.logger = logger

    async def get(
        self, status: Optional[str] = None
    ) -> dict[int, ShopifyBatchProcessORM]:
        async with session_scope(self._session_factory) as session:
            if status:
                where = (ShopifyBatchProcessORM.status == status,)

            else:
                where = ()

            stmt = select(ShopifyBatchProcessORM).where(*where)

            result = await session.execute(stmt)

            batches = {batch.id: batch for batch in result.scalars().all()}
            self.logger.debug(f"Fetched {len(batches)} batch processes")
            return batches

    async def create_batch_process(self, batch_process: ShopifyBatchProcessORM) -> None:
        async with session_scope(self._session_factory) as session:
            session.add(batch_process)
            await session.commit()
            self.logger.info(
                f"Created batch process with id={batch_process.id} for store_id={batch_process.store_id}"
            )

    async def update_batch_process(self, batch_process: ShopifyBatchProcessORM) -> None:
        async with session_scope(self._session_factory) as session:
            stmt = (
                update(ShopifyBatchProcessORM)
                .where(ShopifyBatchProcessORM.id == batch_process.id)
                .values(
                    shopify_id=batch_process.shopify_id,
                    operation=batch_process.operation,
                    status=batch_process.status,
                    objects_count=batch_process.objects_count,
                    objects_processed=batch_process.objects_processed,
                    query=batch_process.query,
                    variables=batch_process.variables,
                    result=batch_process.result,
                )
            )
            await session.execute(stmt)
            self.logger.info(
                f"Updated batch process with id={batch_process.id} for store_id={batch_process.store_id}"
            )

    async def update_status(self, batch_id: int, status: str) -> None:
        async with session_scope(self._session_factory) as session:
            stmt = (
                update(ShopifyBatchProcessORM)
                .where(ShopifyBatchProcessORM.id == batch_id)
                .values(status=status)
            )
            await session.execute(stmt)
            self.logger.info(
                f"Updated status of batch process with id={batch_id} to {status}"
            )
