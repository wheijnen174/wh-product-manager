from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.products.product import ProductORM
from wh_product_manager.db.models.properties.assignment import (
    ProductPropertyAssignmentORM,
)
from wh_product_manager.db.models.properties.definition import PropertyDefinitionORM
from wh_product_manager.db.models.properties.value import PropertyValueORM
from wh_product_manager.db.session_utils import session_scope
from wh_product_manager.properties.data_processing import db_unique_value_key
from wh_product_manager.properties.schemas.definition import UnifiedPropertyDefinition
from wh_product_manager.suppliers.base import SupplierDataResult


class PropertyDomainRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], logger: Logger
    ):
        self._session_factory = session_factory
        self.logger = logger

    async def create_definitions_and_values(
        self, properties_data: dict[str, UnifiedPropertyDefinition]
    ) -> dict[str, Any]:
        self.logger.info(
            "Creating property definitions and values in PropertyDomainRepository"
        )

        fetched_properties = await self._fetch_existing_property_definitions()

        new_properties: dict[str, PropertyDefinitionORM] = {}
        new_values: dict[int, list[PropertyValueORM]] = {}

        for prop_key, prop in properties_data.items():
            existing_prop = fetched_properties.get(prop_key)
            if existing_prop is None:
                new_properties[prop_key] = prop.to_orm()
                continue

            # Handle existing properties if needed
            existing_values = [
                db_unique_value_key(val.normalized_value)
                for val in existing_prop.values
            ]
            missing_values = [
                val.to_orm()
                for val in prop.values
                if db_unique_value_key(val.normalized_value) not in existing_values
            ]

            if len(missing_values) > 0:
                if existing_prop.id not in new_values:
                    new_values[existing_prop.id] = []

                new_values[existing_prop.id].extend(missing_values)

        if len(new_properties) > 0 or len(new_values) > 0:
            created_properties = await self._insert_definitions_with_values(
                new_properties
            )
            created_values = await self._insert_values_for_definition(new_values)

            no_of_created_defs = len(created_properties)
            no_of_created_values = sum(len(v) for v in created_values.values())

            self.logger.info(
                f"Created {no_of_created_defs} property definitions and {no_of_created_values} property values in PropertyDomainRepository"
            )
        else:
            no_of_created_defs = 0
            no_of_created_values = 0

            self.logger.info(
                "No new property definitions or values to create in PropertyDomainRepository"
            )

        upsert_result = {
            "necessary_properties": len(properties_data),
            "new_property_definitions_with_values": no_of_created_defs,
            "new_property_values_for_existing_definitions": no_of_created_values,
        }
        return upsert_result

    async def create_assignments(
        self, all_products: SupplierDataResult, created_products: list[ProductORM]
    ) -> dict[str, Any]:
        if not all_products.products:
            self.logger.warning(
                "No products found in supplier data. Skipping property assignment creation."
            )
            return {
                "error": "No products found in supplier data. Property assignment creation skipped.",
            }

        if not created_products or len(created_products) == 0:
            self.logger.info(
                "No new products created. Skipping property assignment creation."
            )
            return {
                "new_products": 0,
                "properties_assigned": 0,
            }

        self.logger.info(
            "Starting property assignment creation in PropertyDomainRepository"
        )

        # Filter list of created_products to only contain the data necessary for product matching
        products_map: dict[str, int] = {
            ("-".join([prod.supplier_name, prod.parent_sku])): prod.id
            for prod in created_products
        }
        supplier_name = all_products.supplier_name

        # Fetch all property definitions and values to minimize DB queries during assignment creation
        all_properties = await self._fetch_existing_property_definitions()

        assignments: list[ProductPropertyAssignmentORM] = []

        for parent_sku, product in all_products.products.items():
            assignable_product = products_map.get("-".join([supplier_name, parent_sku]))

            if not product.properties or not assignable_product:
                continue

            product_id = assignable_product

            for prop in product.properties:
                assignable_definition = all_properties.get(prop.key)
                if not assignable_definition:
                    self.logger.warning(
                        f"Property definition with key '{prop.key}' not found in DB for assignment creation. Skipping assignment for this property."
                    )
                    continue

                property_definition_id = assignable_definition.id
                assignable_values = {
                    db_unique_value_key(value.normalized_value): value.id
                    for value in assignable_definition.values
                }

                for value in prop.values:
                    assignable_value_id = assignable_values.get(
                        db_unique_value_key(value.normalized_value)
                    )

                    if not assignable_value_id:
                        self.logger.warning(
                            f"Property value with normalized value '{value.normalized_value}' not found in DB for property definition '{prop.key}' during assignment creation. Skipping assignment for this value."
                        )
                        continue

                    property_value_id = assignable_value_id
                    raw_value = value.display_value

                    assignments.append(
                        ProductPropertyAssignmentORM(
                            product_id=product_id,
                            property_definition_id=property_definition_id,
                            property_value_id=property_value_id,
                            raw_value=raw_value,
                            source="supplier",
                            assigned_by="supplier_feed",
                        )
                    )

        async with session_scope(self._session_factory) as session:
            session.add_all(assignments)
            await session.commit()

        result_summary = {
            "new_products": len(created_products),
            "properties_assigned": len(assignments),
        }
        return result_summary

    async def _insert_definitions_with_values(
        self, new_properties: dict[str, PropertyDefinitionORM]
    ) -> dict[str, PropertyDefinitionORM]:
        if len(new_properties) > 0:
            for definition in new_properties.values():
                deduped_values: dict[str, PropertyValueORM] = {}
                for value in definition.values:
                    dedupe_key = db_unique_value_key(value.normalized_value)
                    if dedupe_key in deduped_values:
                        continue

                    value.normalized_value = db_unique_value_key(value.normalized_value)
                    deduped_values[dedupe_key] = value

                if len(deduped_values) != len(definition.values):
                    self.logger.warning(
                        "Property '%s' had duplicate values after canonicalization: %s -> %s",
                        definition.key,
                        len(definition.values),
                        len(deduped_values),
                    )

                definition.values = list(deduped_values.values())

            async with session_scope(self._session_factory) as session:
                session.add_all(list(new_properties.values()))
                await session.commit()

        return new_properties

    async def _insert_values_for_definition(
        self, new_values: dict[int, list[PropertyValueORM]]
    ) -> dict[int, list[PropertyValueORM]]:
        if len(new_values) > 0:
            for definition_id, values in new_values.items():
                for value in values:
                    value.property_definition_id = definition_id
                    value.normalized_value = db_unique_value_key(value.normalized_value)

            async with session_scope(self._session_factory) as session:
                session.add_all(
                    [
                        value
                        for values_list in new_values.values()
                        for value in values_list
                    ]
                )
                await session.commit()

        return new_values

    async def _fetch_existing_property_definitions(
        self,
    ) -> dict[str, PropertyDefinitionORM]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PropertyDefinitionORM).options(
                    selectinload(PropertyDefinitionORM.values)
                )
            )
            properties = result.scalars().unique().all()
            return {prop.key: prop for prop in properties}
