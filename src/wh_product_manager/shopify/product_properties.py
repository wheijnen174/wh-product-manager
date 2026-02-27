from typing import Any

from slugify import slugify

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.metafields import MetafieldService
from wh_product_manager.shopify.metaobjects import MetaobjectService
from wh_product_manager.suppliers.schemas import UnifiedProduct


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
        self, products: dict[str, UnifiedProduct], category_constraints: list[str]
    ) -> dict[str, UnifiedProduct]:
        self.logger.info("Start processing product properties")

        namespace = "Product"

        all_properties = await self._get_all_properties(products, namespace)

        all_properties = await self._prepare_property_definitions(
            all_properties, namespace, category_constraints
        )

        all_properties = await self._prepare_property_values(all_properties)

        products = await self._assign_properties_to_products(products, all_properties)

        self.logger.info("Finished processing product properties")

        return products

    async def _get_all_properties(
        self, products: dict[str, UnifiedProduct], namespace: str
    ) -> dict[str, dict[str, Any]]:
        self.logger.debug("Extracting all properties from products")

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

                if details.field_type == "metafield":
                    if property_title not in all_properties:
                        all_properties[property_title] = {
                            "namespace": namespace,
                            "key": slugify(property_title, separator="_"),
                            "single_or_multi": details.single_or_multi,
                            "field_type": details.field_type,
                            "values": [],
                        }
                    continue

                # Add the metaobject property to the all_properties dictionary if it doesn't exist yet, using the property title as the dict-key
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
            details["values"] = {str(val): None for val in details["values"]}

        self.logger.debug("Extracted all properties from products")
        return all_properties

    async def _prepare_property_definitions(
        self,
        all_properties: dict[str, dict[str, Any]],
        namespace: str,
        category_constraints: list[str],
    ) -> dict[str, dict[str, Any]]:
        self.logger.debug("Preparing property definitions")

        # Step 1: get existing metaobjects
        metaobject_definitions: dict[
            str, Any
        ] = await self.metaobject_service.get_definitions()
        metaobject_definitions = {
            key: {
                "id": value["id"],
                "type": value["type"],
                "values": {
                    str(list(details["values"].values())[0]): details["id"]
                    for details in value["values"].values()
                },
            }
            for key, value in metaobject_definitions.items()
            if value["type"].split("-")[0] == slugify(namespace, separator="_")
        }

        # Step 2: get existing metafields
        metafield_definitions: dict[
            str, Any
        ] = await self.metafield_service.get_definitions(
            owner_type="PRODUCT", namespace=slugify(namespace, separator="_")
        )

        # Step 3: add IDs to all_properties based on existing metaobjects and metafields
        for property_title, details in all_properties.items():
            is_metaobject = details["field_type"] == "metaobject"

            metaobject_exists = (
                namespace + " - " + property_title
            ) in metaobject_definitions

            metafield_exists = property_title in metafield_definitions

            # Create metaobject for property if it is a metaobject and doesn't exist
            if is_metaobject:
                # If the metaobject already exists, use it. Otherwise, create it and use the created version.
                if metaobject_exists:
                    metaobject: dict[str, Any] = metaobject_definitions[
                        namespace + " - " + property_title
                    ]
                else:
                    metaobject: dict[
                        str, Any
                    ] = await self.metaobject_service.create_definition(
                        name=property_title, details=details
                    )

                # Add the value ID to the all_properties dictionary for each existing value of the property
                for value_name, value_id in details["values"].items():
                    value_id = metaobject["values"].get(value_name, None)
                    all_properties[property_title]["values"][value_name] = value_id

                # Create any missing values for the metaobject and update the all_properties dictionary with the created value IDs
                # Checking if values are missing is done by function 'create_missing_values'
                all_properties[property_title][
                    "values"
                ] = await self.metaobject_service.create_missing_values(
                    metaobject["type"], details["key"], details["values"]
                )

            # Create metafield for property if it doesn't exist
            if metafield_exists:
                metafield: dict[str, Any] = metafield_definitions[property_title]  # type: ignore # noqa: F841
            else:
                definition: dict[str, Any] = {
                    "ownerType": "PRODUCT",
                    "namespace": slugify(namespace, separator="_"),
                    "key": details["key"],
                    "name": property_title,
                    "constraints": {
                        "key": "category",
                        "values": category_constraints,
                    },
                    "access": {"storefront": "PUBLIC_READ"},
                    "capabilities": {
                        "adminFilterable": {"enabled": False}
                    },  # see note below
                }

                # NOTE: METAFIELD ADMIN FILTERABLE:
                #   Only 50 metafields can be marked as adminFilterable, so we won't enable it for any of the properties for now.
                #   This means that these metafields won't be available as filters in the Shopify admin, but it also means that
                #   we won't run into the limit of 50 adminFilterable metafields.

                if is_metaobject:
                    if details["single_or_multi"] == "single":
                        definition["type"] = "metaobject_reference"
                    else:
                        definition["type"] = "list.metaobject_reference"

                    definition["validations"] = [
                        {
                            "name": "metaobject_definition_id",
                            "value": metaobject["id"],  # type: ignore
                        }
                    ]

                else:
                    if details["single_or_multi"] == "single":
                        definition["type"] = "single_line_text_field"
                    else:
                        definition["type"] = "list.single_line_text_field"

                metafield: dict[  # type: ignore # noqa: F841
                    str, Any
                ] = await self.metafield_service.create_definition(
                    variables={"definition": definition}
                )

        self.logger.debug("Prepared property definitions")
        return all_properties

    async def _prepare_property_values(
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

            processed_properties: dict[str, str | list[str]] = {}
            if product.properties is not None:
                for property_title, details in product.properties.items():
                    existing_property = all_properties.get(property_title) or None

                    if existing_property is not None:
                        if details.field_type == "metafield":
                            name: str = (
                                existing_property["namespace"]
                                + "."
                                + existing_property["key"]
                            )

                            processed_properties[name.lower()] = details.values

                        elif details.field_type == "metaobject":
                            name: str = (
                                existing_property["namespace"]
                                + "."
                                + existing_property["key"]
                            )

                            if isinstance(details.values, str):
                                values = existing_property["values"].get(
                                    details.values, None
                                )

                            else:
                                values = [
                                    existing_property["values"].get(val, None)
                                    for val in details.values
                                ]

                            if values is not None:
                                processed_properties[name.lower()] = values

            for name, values in processed_properties.items():
                if isinstance(values, list):
                    processed_properties[name] = list(set(values))

            product.extra_data["processed_properties"] = processed_properties

        return products
