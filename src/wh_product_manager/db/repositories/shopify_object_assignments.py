from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.shopify.object_assignments import (
    ShopifyObjectAssignmentORM,
)
from wh_product_manager.db.session_utils import session_scope


class ShopifyObjectAssignmentsRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], logger: Logger
    ):
        self._session_factory = session_factory
        self.logger = logger

    async def get_object_assignments(self) -> dict[int, dict[str, Any]]:
        self.logger.debug("Loading Shopify object assignments")
        async with session_scope(self._session_factory) as session:
            stmt = select(ShopifyObjectAssignmentORM).where(
                ShopifyObjectAssignmentORM.local_object_type.in_(("product", "variant"))
            )

            result = await session.execute(stmt)
            assignments = result.scalars().unique().all()

            assignments_dict: dict[int, dict[str, Any]] = {}
            for item in assignments:
                store_assignments = assignments_dict.setdefault(
                    item.store_id,
                    {
                        "products": {},
                        "variants": {},
                    },
                )

                if item.local_object_type == "product":
                    store_assignments["products"][item.local_object_id] = {
                        "shopify_id": item.shopify_id,
                        "is_active": item.is_active,
                    }

                elif item.local_object_type == "variant":
                    store_assignments["variants"][item.local_object_id] = {
                        "shopify_id": item.shopify_id,
                        "is_active": item.is_active,
                    }

            self.logger.debug(
                f"Loaded Shopify object assignments (count={len(assignments)})"
            )
            return assignments_dict

    async def get_object_assignments_by_store(self, store_id: int) -> dict[str, Any]:
        self.logger.debug(f"Loading Shopify object assignments for store_id {store_id}")
        async with session_scope(self._session_factory) as session:
            stmt = select(ShopifyObjectAssignmentORM).where(
                ShopifyObjectAssignmentORM.store_id == store_id,
                ShopifyObjectAssignmentORM.local_object_type.in_(
                    ("product", "variant")
                ),
            )

            result = await session.execute(stmt)
            assignments = result.scalars().unique().all()

            assignments_dict: dict[str, Any] = {
                "products": {},
                "variants": {},
            }
            for item in assignments:
                if item.local_object_type == "product":
                    assignments_dict["products"][item.local_object_id] = {
                        "shopify_id": item.shopify_id,
                        "is_active": item.is_active,
                    }

                elif item.local_object_type == "variant":
                    assignments_dict["variants"][item.local_object_id] = {
                        "shopify_id": item.shopify_id,
                        "is_active": item.is_active,
                    }

            self.logger.debug(
                f"Loaded Shopify object assignments (count={len(assignments)})"
            )
            return assignments_dict

    async def create_assignment(
        self, assignment: ShopifyObjectAssignmentORM
    ) -> ShopifyObjectAssignmentORM:
        self.logger.debug(
            f"Creating Shopify object assignment for store_id {assignment.store_id}, "
            f"local_object_type {assignment.local_object_type}, "
            f"local_object_id {assignment.local_object_id}"
        )

        async with session_scope(self._session_factory) as session:
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)
            self.logger.debug(
                f"Created Shopify object assignment with id {assignment.id}"
            )
            return assignment
