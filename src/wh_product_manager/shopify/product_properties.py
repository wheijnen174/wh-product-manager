from typing import Any

from slugify import slugify

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.metafields import MetafieldService
from wh_product_manager.shopify.metaobjects import MetaobjectService
from wh_product_manager.suppliers.schemas import UnifiedProduct
from wh_product_manager.utils.data_loader import save_json


class ProductPropertiesService:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
        metafield_service: MetafieldService,
        metaobject_service: MetaobjectService,
    ):
        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.metafield_service = metafield_service
        self.metaobject_service = metaobject_service

    async def process_properties(
        self, products: dict[str, UnifiedProduct]
    ) -> dict[str, UnifiedProduct]:

        all_properties = await self._get_all_properties(products)

        all_properties = await self._prepare_metafield_definitions(all_properties)

        all_properties = await self._prepare_metafield_values(all_properties)

        products = await self._assign_properties_to_products(products, all_properties)

        save_json("_debug_properties.json", all_properties, True, True)
        save_json(
            "_debug_products.json",
            {parent_sku: product.to_dict() for parent_sku, product in products.items()},
            indent=True,
        )
        raise NotImplementedError(
            "This method is not fully implemented yet. It currently only processes the 'Maat' property and does not handle other properties or metafields."
        )

        return products

    async def _get_all_properties(
        self, products: dict[str, UnifiedProduct]
    ) -> dict[str, dict[str, Any]]:
        namespace = "Product"

        # Initialize the dictionary to hold all properties
        # Add the "Maat" property as a metaobject with an empty list of values
        all_properties: dict[str, dict[str, Any]] = {
            "Maat": {
                "namespace": namespace,
                "key": "maat",
                "single_or_multi": "multi",
                "field_type": "metaobject",
                "values": [],
            }
        }

        # List to keep track of properties that should be dropped due to conflicts or other issues
        properties_to_drop: list[str] = []

        for parent_sku, product in products.items():
            # Extract size titles from product variants and add them to the "Maat" property if they are not already present
            all_properties["Maat"]["values"].extend(
                [
                    var.size_title
                    for var in product.variants
                    if var.size_title is not None
                    and var.size_title not in all_properties["Maat"]["values"]
                ]
            )

            if product.properties is None:
                continue

            for property_title, details in product.properties.items():
                if property_title == "Maat":
                    self.logger.warning(
                        f"Skipping property '{property_title}' for product '{parent_sku}' since it's already handled as a metaobject"
                    )
                    continue  # Skip processing the "Maat" property since it's already handled as a metaobject

                if property_title in properties_to_drop:
                    continue  # Skip processing this property since it's already marked for dropping

                # Add the property to the all_properties dictionary if it doesn't exist yet, using the property title as the dict-key
                if property_title not in all_properties:
                    all_properties[property_title] = {
                        "namespace": namespace,
                        "key": slugify(property_title, separator="_"),
                        "single_or_multi": details.single_or_multi,
                        "field_type": details.field_type,
                        "values": [],
                    }

                # Check for conflicts in single_or_multi if the property already exists
                elif (
                    property_title in all_properties
                    and details.single_or_multi
                    != all_properties[property_title]["single_or_multi"]
                ):
                    properties_to_drop.append(property_title)
                    self.logger.warning(
                        f"Conflict for property '{property_title}': single_or_multi mismatch (existing: {all_properties[property_title]['single_or_multi']}, new: {details.single_or_multi})"
                    )
                    continue  # Skip adding values for this property since it has a field_type conflict

                # Check for conflicts in field_type if the property already exists
                elif (
                    property_title in all_properties
                    and details.field_type
                    != all_properties[property_title]["field_type"]
                ):
                    properties_to_drop.append(property_title)
                    self.logger.warning(
                        f"Conflict for property '{property_title}': field_type mismatch (existing: {all_properties[property_title]['field_type']}, new: {details.field_type})"
                    )
                    continue  # Skip adding values for this property since it has a field_type conflict

                # Add the property values to the all_properties dictionary, ensuring no duplicates
                if (
                    isinstance(details.values, str)
                    and details.values not in all_properties[property_title]["values"]
                ):
                    all_properties[property_title]["values"].append(details.values)
                elif isinstance(details.values, list):
                    all_properties[property_title]["values"].extend(
                        [
                            val
                            for val in details.values
                            if val not in all_properties[property_title]["values"]
                        ]
                    )

        for property_title in properties_to_drop:
            del all_properties[property_title]

        for property_title, details in all_properties.items():
            details["shopify_data"] = {
                "metafield_id": None,
                "metaobject_id": None,
            }

            details["values"] = {str(val): None for val in details["values"]}

        return all_properties

    async def _prepare_metafield_definitions(
        self, all_properties: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        # Step 1: get existing metaobjects
        metaobject_definitions = await self.metaobject_service.get_definitions()  # type: ignore  # noqa: F841

        # Step 2: get existing metafields
        metafield_definitions = await self.metafield_service.get_definitions()  # type: ignore # noqa: F841

        # Step 3: add IDs to all_properties based on existing metaobjects and metafields
        # Step 4: create missing metaobjects
        # Step 5: create missing metafields

        return all_properties

    async def _prepare_metafield_values(
        self, all_properties: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        return all_properties

    async def _assign_properties_to_products(
        self,
        products: dict[str, UnifiedProduct],
        all_properties: dict[str, dict[str, Any]],
    ) -> dict[str, UnifiedProduct]:
        for product in products.values():
            for variant in product.variants:
                variant.size_title = (
                    all_properties["Maat"]["values"][variant.size_title]
                    if variant.size_title in all_properties["Maat"]["values"]
                    else None
                )

            processed_properties = {}
            if product.properties is not None:
                for property_title, details in product.properties.items():
                    property_id: str = (
                        all_properties.get(property_title, {})
                        .get("shopify_data", {})
                        .get("metafield_id")
                    )
                    if isinstance(details.values, str):
                        property_values_ids = all_properties.get(
                            property_title, {}
                        ).get("values", [])[details.values]
                    else:
                        property_values_ids = [
                            all_properties.get(property_title, {}).get("values", [])[
                                val
                            ]
                            for val in details.values
                        ]

                    if property_id and property_values_ids:
                        processed_properties[property_id] = property_values_ids

            product.extra_data["processed_properties"] = processed_properties

        return products
