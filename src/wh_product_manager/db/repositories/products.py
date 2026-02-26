from sqlalchemy import (
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wh_product_manager.db.models.products import Products, ProductsTexts
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

    async def upsert_text(
        self,
        *,
        product_id: int,
        field: str,
        source: str,
        language: str,
        text_value: str,
    ) -> None:
        """
        Portable upsert approach using ORM:
        - find existing row
        - update or insert
        (Later you can replace with MariaDB ON DUPLICATE KEY UPDATE for speed.)
        """
        f = field.strip().lower()
        s = source.strip().lower()
        lang = language.strip().lower()

        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(ProductsTexts).where(
                    ProductsTexts.product_id == product_id,
                    ProductsTexts.field == f,
                    ProductsTexts.source == s,
                    ProductsTexts.language == lang,
                )
            )
            row = res.scalar_one_or_none()

            if row is None:
                session.add(
                    ProductsTexts(
                        product_id=product_id,
                        field=f,
                        source=s,
                        language=lang,
                        text=text_value,
                    )
                )
            else:
                row.text = text_value

    async def get_text(
        self,
        *,
        product_id: int,
        field: str,
        source: str,
        language: str,
    ) -> str | None:
        f = field.strip().lower()
        s = source.strip().lower()
        lang = language.strip().lower()

        async with session_scope(self._session_factory) as session:
            res = await session.execute(
                select(ProductsTexts.text).where(
                    ProductsTexts.product_id == product_id,
                    ProductsTexts.field == f,
                    ProductsTexts.source == s,
                    ProductsTexts.language == lang,
                )
            )
            return res.scalar_one_or_none()
