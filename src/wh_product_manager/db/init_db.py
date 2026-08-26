from sqlalchemy.ext.asyncio import AsyncEngine

from wh_product_manager.db.base_model import Base

# Ensure ORM models are imported so Base.metadata is fully populated.
from wh_product_manager.db.models import (
    collections,  # type: ignore # noqa: F401
    country_mapping,  # type: ignore # noqa: F401,  # type: ignore # noqa: F401
)
from wh_product_manager.db.models.products import (
    description,  # type: ignore # noqa: F401
    media,  # type: ignore # noqa: F401
    product,  # type: ignore # noqa: F401
    text_field,  # type: ignore # noqa: F401
    variant,  # type: ignore # noqa: F401
)
from wh_product_manager.db.models.properties import (
    assignment,  # type: ignore # noqa: F401
    definition,  # type: ignore # noqa: F401
    sync_state,  # type: ignore # noqa: F401
    value,  # type: ignore # noqa: F401
)
from wh_product_manager.db.models.shopify import (
    batch_processes,  # type: ignore # noqa: F401
    category_taxonomies,  # type: ignore # noqa: F401
    object_assignments,  # type: ignore # noqa: F401
    store_authentication,  # type: ignore # noqa: F401
)


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
