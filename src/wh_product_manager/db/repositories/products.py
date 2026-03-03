from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.db.models.products import Products
from wh_product_manager.db.session_utils import session_scope


class ProductsRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_or_create_product(
        self, *, supplier_name: str, parent_sku: str
    ) -> Products:
        supplier = supplier_name.strip()
        sku = parent_sku.strip()

        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(Products).where(
                    Products.supplier_name == supplier,
                    Products.parent_sku == sku,
                )
            )
            product = res.scalar_one_or_none()
            if product:
                return product

            product = Products(supplier_name=supplier, parent_sku=sku)
            session.add(product)
            await session.flush()  # assigns product.id
            return product

    async def upsert_property(
        self,
        *,
        product_id: int,
        field: str,
        source: str,
        language: str,
        value: str,
    ) -> None:
        stmt = text(
            """
                INSERT INTO products_properties (product_id, field, source, language, value)
                VALUES (:product_id, :field, :source, :language, :value)
                ON DUPLICATE KEY UPDATE
                    value = VALUES(value)
            """
        )

        async with session_scope(self._session_factory) as session:
            await session.execute(
                stmt,
                {
                    "product_id": product_id,
                    "field": field,
                    "source": source,
                    "language": language,
                    "value": value,
                },
            )
