from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.products.product import ProductORM
from wh_product_manager.db.models.products.variant import VariantORM
from wh_product_manager.db.session_utils import session_scope
from wh_product_manager.suppliers.base import SupplierDataResult


class ProductsRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], logger: Logger
    ):
        self._session_factory = session_factory
        self.logger = logger

    async def get_products_by_supplier(
        self, supplier_name: str, full_detail: bool = True
    ) -> dict[str, dict[str, Any]]:
        self.logger.debug(
            f"{supplier_name} - Loading products by supplier (full_detail={full_detail})"
        )
        async with session_scope(self._session_factory) as session:
            if full_detail:
                options = (
                    selectinload(ProductORM.description),
                    selectinload(ProductORM.title),
                    selectinload(ProductORM.supplier_category),
                    selectinload(ProductORM.shopify_category),
                    selectinload(ProductORM.shopify_collections),
                    selectinload(ProductORM.variants).selectinload(
                        VariantORM.shopify_assignments
                    ),
                    selectinload(ProductORM.media),
                    selectinload(ProductORM.shopify_assignments),
                )

            else:
                options = (selectinload(ProductORM.variants),)

            stmt = (
                select(ProductORM)
                .where(ProductORM.supplier_name == supplier_name)
                .options(*options)
            )

            result = await session.execute(stmt)
            products = result.scalars().unique().all()

            if full_detail:
                self.logger.debug(
                    f"{supplier_name} - Loaded full-detail products (count={len(products)})"
                )
                return {
                    product.parent_sku: self._serialize_full_product(product)
                    for product in products
                }

            self.logger.debug(
                f"{supplier_name} - Loaded minimal products (count={len(products)})"
            )
            return {
                product.parent_sku: self._serialize_minimal_product(product)
                for product in products
            }

    async def get_products_by_ids(
        self, product_ids: list[int], full_detail: bool = True
    ) -> dict[int, ProductORM]:
        self.logger.debug(f"Loading products by IDs: {product_ids}")

        if full_detail:
            options = (
                selectinload(ProductORM.description),
                selectinload(ProductORM.title),
                selectinload(ProductORM.supplier_category),
                selectinload(ProductORM.shopify_category),
                selectinload(ProductORM.shopify_collections),
                selectinload(ProductORM.variants).selectinload(
                    VariantORM.shopify_assignments
                ),
                selectinload(ProductORM.media),
                selectinload(ProductORM.shopify_assignments),
            )
        else:
            options = (
                selectinload(ProductORM.variants).selectinload(
                    VariantORM.shopify_assignments
                ),
                selectinload(ProductORM.shopify_assignments),
            )

        async with session_scope(self._session_factory) as session:
            stmt = (
                select(ProductORM)
                .where(ProductORM.id.in_(product_ids))
                .options(*options)
            )

            result = await session.execute(stmt)
            products = result.scalars().unique().all()

            self.logger.debug(f"Loaded products by IDs (count={len(products)})")
            return {product.id: product for product in products}

    async def get_products_for_shopify_creation(self) -> dict[int, dict[str, Any]]:
        self.logger.debug("Loading products for Shopify creation")
        async with session_scope(self._session_factory) as session:
            stmt = select(ProductORM).options(selectinload(ProductORM.variants))

            result = await session.execute(stmt)
            products = result.scalars().unique().all()

            self.logger.debug(
                f"Loaded products for Shopify creation (count={len(products)})"
            )
            return {
                product.id: {
                    "is_publishable": product.is_publishable,
                    "is_missing": product.is_missing,
                    "variants": {
                        variant.id: variant.is_missing
                        for variant in (product.variants or [])
                    },
                }
                for product in products
            }

    async def upsert_products_and_variants(
        self,
        supplier_data: SupplierDataResult,
    ) -> tuple[dict[str, Any], list[ProductORM]]:
        # Step 0: check if supplier_data contains products
        if not supplier_data.products:
            raise ValueError(
                f"{supplier_data.supplier_name} - No products found in supplier data for upsert"
            )

        # Step 1: set all stock to zero for existing products for the supplier
        await self._set_all_stock_zero(supplier_data.supplier_name)

        # Step 2: convert supplier data to ORM objects
        self.logger.info(
            f"{supplier_data.supplier_name} - Converting supplier data to ORM objects"
        )
        products: list[ProductORM] = [
            prod.to_orm() for prod in supplier_data.products.values()
        ]

        # Step 3: split new and existing products
        self.logger.info(
            f"{supplier_data.supplier_name} - Splitting supplier data into new and existing products"
        )
        (
            new_products,
            existing_products,
            split_data_results,
        ) = await self._split_supplier_data(products, supplier_data.supplier_name)

        # Step 4: update existing products and variants and insert new variants for existing products
        self.logger.info(
            f"{supplier_data.supplier_name} - Updating existing products and variants and inserting new variants for existing products (count={len(existing_products)})"
        )
        existing_update_result = await self._update_existing_products_and_variants(
            existing_products
        )

        # Step 5: insert new products and variants
        self.logger.info(
            f"{supplier_data.supplier_name} - Inserting new products and variants (count={len(new_products)})"
        )
        new_products_insert_result = await self._insert_new_products_and_variants(
            new_products
        )

        self.logger.info(
            f"{supplier_data.supplier_name} - Product upsert complete:\n\t\tExisting products updated: {existing_update_result}\n\t\tNew products inserted: {new_products_insert_result}"
        )

        upsert_result = {
            "split_data_results": split_data_results,
            "existing_update_result": existing_update_result,
            "new_products_insert_result": new_products_insert_result,
        }
        return upsert_result, new_products

    async def _insert_new_products_and_variants(
        self, new_products: list[ProductORM]
    ) -> dict[str, Any]:
        async with session_scope(self._session_factory) as session:
            session.add_all(new_products)
            await session.commit()

        return {"inserted_products_count": len(new_products)}

    async def _update_existing_products_and_variants(
        self, existing_products: list[ProductORM]
    ) -> dict[str, Any]:
        last_seen_at = None
        product_ids: list[int] = []
        rows: list[dict[str, Any]] = []

        for product in existing_products:
            if not product.id:
                self.logger.warning(
                    f"{product.supplier_name} - Existing product with parent_sku {product.parent_sku} does not have an ID, skipping variant upsert"
                )
                continue

            if product.id not in product_ids:
                product_ids.append(product.id)

            for variant in product.variants or []:
                last_seen_at = variant.last_seen_at

                rows.append(
                    {
                        "product_id": product.id,
                        "supplier_name": variant.supplier_name,
                        "sku": variant.sku,
                        "size_title": variant.size_title,
                        "stock": variant.stock,
                        "price": variant.price,
                        "cost": variant.cost,
                        "rrp": variant.rrp,
                        "barcode": variant.barcode,
                        "weight": variant.weight,
                        "country_of_origin": variant.country_of_origin,
                        "hscode": variant.hscode,
                        "last_seen_at": variant.last_seen_at,
                        "missing_since": variant.missing_since,
                        "is_missing": variant.is_missing,
                    }
                )

        if len(product_ids) > 0 or len(rows) > 0:
            async with session_scope(self._session_factory) as session:
                if len(product_ids) > 0:
                    stmt = (
                        update(ProductORM)
                        .where(ProductORM.id.in_(product_ids))
                        .values(
                            last_seen_at=last_seen_at or ProductORM.last_seen_at,
                            missing_since=None,
                            is_missing=False,
                        )
                    )
                    await session.execute(stmt)

                if len(rows) > 0:
                    stmt = mysql_insert(VariantORM).values(rows)

                    # Use inserted.<col> to refer to incoming values on conflict
                    upsert_stmt = stmt.on_duplicate_key_update(
                        product_id=stmt.inserted.product_id,
                        size_title=stmt.inserted.size_title,
                        stock=stmt.inserted.stock,
                        price=stmt.inserted.price,
                        cost=stmt.inserted.cost,
                        rrp=stmt.inserted.rrp,
                        barcode=stmt.inserted.barcode,
                        weight=stmt.inserted.weight,
                        country_of_origin=stmt.inserted.country_of_origin,
                        hscode=stmt.inserted.hscode,
                        last_seen_at=stmt.inserted.last_seen_at,
                        missing_since=None,
                        is_missing=stmt.inserted.is_missing,
                    )
                    await session.execute(upsert_stmt)

        return {
            "updated_products_count": len(product_ids),
            "upserted_variants_count": len(rows),
        }

    async def _split_supplier_data(
        self, products: list[ProductORM], supplier_name: str
    ) -> tuple[list[ProductORM], list[ProductORM], dict[str, Any]]:
        existing_skus = await self.get_products_by_supplier(
            supplier_name, full_detail=False
        )

        new_products: list[ProductORM] = []
        existing_products: list[ProductORM] = []

        for product in products:
            existing_product = existing_skus.get(product.parent_sku)
            if existing_product is None:
                new_products.append(product)
                continue

            product.id = existing_product["id"]
            existing_products.append(product)

        return (
            new_products,
            existing_products,
            {
                "total_products_count": len(products),
                "new_products_count": len(new_products),
                "existing_products_count": len(existing_products),
                "missing_products_count": len(existing_skus) - len(existing_products),
            },
        )

    async def _set_all_stock_zero(self, supplier_name: Optional[str] = None) -> None:
        self.logger.info(
            f"{supplier_name or 'ALL SUPPLIERS'} - Setting stock to zero for all variants for supplier"
        )
        async with session_scope(self._session_factory) as session:
            if supplier_name:
                # Neutralize all products
                stmt = (
                    update(ProductORM)
                    .where(ProductORM.supplier_name == supplier_name)
                    .values(missing_since=ProductORM.last_seen_at, is_missing=True)
                )
                await session.execute(stmt)

                # Neutralize all variants
                stmt = (
                    update(VariantORM)
                    .where(VariantORM.supplier_name == supplier_name)
                    .values(
                        stock=0, missing_since=VariantORM.last_seen_at, is_missing=True
                    )
                )
                await session.execute(stmt)
            else:
                # Neutralize all products
                stmt = update(ProductORM).values(
                    missing_since=ProductORM.last_seen_at, is_missing=True
                )
                await session.execute(stmt)

                # Neutralize all variants
                stmt = update(VariantORM).values(
                    stock=0, missing_since=VariantORM.last_seen_at, is_missing=True
                )
                await session.execute(stmt)

    @staticmethod
    def _source_value_map(items: list[Any]) -> dict[str, str]:
        return {item.source: item.value for item in items}

    @staticmethod
    def _serialize_full_product(product: ProductORM) -> dict[str, Any]:
        descriptions = product.description or []
        title = product.title or []
        supplier_category = product.supplier_category or []
        shopify_category = product.shopify_category or []
        shopify_collections = product.shopify_collections or []
        variants = product.variants or []
        media = product.media or []

        return {
            "id": product.id,
            "supplier_name": product.supplier_name,
            "parent_sku": product.parent_sku,
            "supplier_product_id": product.supplier_product_id,
            "model_number": product.model_number,
            "last_seen_at": product.last_seen_at,
            # "created_at": product.created_at,
            # "updated_at": product.updated_at,
            "title": ProductsRepository._source_value_map(title),
            "description": ProductsRepository._source_value_map(descriptions),
            "supplier_category": ProductsRepository._source_value_map(
                supplier_category
            ),
            "shopify_category": ProductsRepository._source_value_map(shopify_category),
            "shopify_collections": ProductsRepository._source_value_map(
                shopify_collections
            ),
            "variants": [
                {
                    "id": variant.id,
                    "sku": variant.sku,
                    "size_title": variant.size_title,
                    "stock": variant.stock,
                    "price": variant.price,
                    "cost": variant.cost,
                    "rrp": variant.rrp,
                    "barcode": variant.barcode,
                    "weight": variant.weight,
                    "country_of_origin": variant.country_of_origin,
                    "hscode": variant.hscode,
                    "shopify_assignments": [
                        assignment.to_dict()
                        for assignment in (variant.shopify_assignments or [])
                    ],
                }
                for variant in variants
            ],
            "media": [
                {
                    "id": item.id,
                    "upload_allowed": item.upload_allowed,
                    "filename": item.filename,
                    "alt_text": item.alt_text,
                    "content_type": item.content_type,
                    "source_url": item.source_url,
                }
                for item in media
            ],
        }

    @staticmethod
    def _serialize_minimal_product(product: ProductORM) -> dict[str, Any]:
        variants = product.variants or []
        return {
            "id": product.id,
            "variant_skus": [variant.sku for variant in variants],
        }
