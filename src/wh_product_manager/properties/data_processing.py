from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.properties.schemas.definition import UnifiedPropertyDefinition
from wh_product_manager.properties.schemas.value import UnifiedPropertyValue
from wh_product_manager.suppliers.base import SupplierDataResult


class PropertyDataProcessor:
    def __init__(self, logger: Logger):
        self.logger = logger

    async def process_properties(
        self, product_data: SupplierDataResult
    ) -> dict[str, UnifiedPropertyDefinition]:

        if not product_data.products:
            self.logger.warning(
                "No products found in supplier data. Skipping property processing."
            )
            return {}

        self.logger.info(
            f"{product_data.supplier_name} - Processing necessary properties for {len(product_data.products)} products from supplier data."
        )

        properties_dict: dict[str, Any] = {}

        for product in product_data.products.values():
            if not product.properties:
                continue

            for prop in product.properties:
                if prop.key not in properties_dict:
                    properties_dict[prop.key] = {
                        "key": prop.key,
                        "label": prop.label,
                        "input_kind": [],
                        "storage_kind": [],
                        "value_type": [],
                        "allow_supplier_create": prop.allow_supplier_create,
                        "allow_ai_assign": prop.allow_ai_assign,
                        "allow_ai_create_values": prop.allow_ai_create_values,
                        "created_by": prop.created_by,
                        "created_by_supplier_name": prop.created_by_supplier_name,
                        "values": [],
                    }

                properties_dict[prop.key]["input_kind"].append(prop.input_kind)
                properties_dict[prop.key]["storage_kind"].append(prop.storage_kind)
                properties_dict[prop.key]["value_type"].append(prop.value_type)
                properties_dict[prop.key]["values"].extend(
                    [
                        val.to_dict()
                        for val in prop.values
                        if val.to_dict() not in properties_dict[prop.key]["values"]
                    ]
                )

        properties: dict[str, UnifiedPropertyDefinition] = {}
        for prop in properties_dict.values():
            # Deduplicate input_kind, storage_kind, value_type, and values
            prop["input_kind"] = sorted(list(set(prop["input_kind"])))
            prop["storage_kind"] = sorted(list(set(prop["storage_kind"])))
            prop["value_type"] = sorted(list(set(prop["value_type"])))

            if len(prop["input_kind"]) == 1:
                prop["input_kind"] = prop["input_kind"][0]
            else:
                prop["input_kind"] = "multi"

            if len(prop["storage_kind"]) == 1:
                prop["storage_kind"] = prop["storage_kind"][0]
            else:
                prop["storage_kind"] = "metaobject_linked"

            if len(prop["value_type"]) == 1:
                prop["value_type"] = prop["value_type"][0]
            else:
                prop["value_type"] = "text"

            deduped_values: dict[str, UnifiedPropertyValue] = {}
            for val in prop["values"]:
                dedupe_key = db_unique_value_key(val["normalized_value"])
                if dedupe_key in deduped_values:
                    continue

                deduped_values[dedupe_key] = UnifiedPropertyValue(
                    normalized_value=val["normalized_value"].strip(),
                    display_value=val["display_value"],
                    created_by=val["created_by"],
                )

            prop["values"] = list(deduped_values.values())

            properties[prop["key"]] = UnifiedPropertyDefinition(
                key=prop["key"],
                label=prop["label"],
                input_kind=prop["input_kind"],
                storage_kind=prop["storage_kind"],
                value_type=prop["value_type"],
                allow_supplier_create=prop["allow_supplier_create"],
                allow_ai_assign=prop["allow_ai_assign"],
                allow_ai_create_values=prop["allow_ai_create_values"],
                created_by=prop["created_by"],
                created_by_supplier_name=prop["created_by_supplier_name"],
                values=prop["values"],
            )

        self.logger.info(
            f"{product_data.supplier_name} - Extracted {len(properties)} unique properties from supplier product data."
        )

        return properties


def db_unique_value_key(normalized_value: str) -> str:
    """Build a canonical key aligned with DB uniqueness behavior."""
    return normalized_value.strip().casefold()
