"""
Shopify product set (parent + variant) operations
Manages creation, updating, and deletion of product sets
"""

from typing import Any
from uuid import uuid4

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.suppliers.schemas import UnifiedProduct


class ProductUpdate:
    """Manages product update operations"""

    def __init__(self, shopify_client: ShopifyGraphQLClient, logger: Logger):
        """
        Initialize product update manager

        Args:
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.logger = logger

    async def prepare_update_mutations(
        self,
        supplier_name: str,
        inventory: dict[str, Any],
        supplier_data: dict[str, UnifiedProduct],
        update_time: str,
    ) -> list[str]:
        mutation_items: list[str] = []

        for idx, (parent_sku, product) in enumerate(supplier_data.items()):
            inventory_item = inventory.get(parent_sku)

            if inventory_item is None or inventory_item.get("variants", []) == []:
                self.logger.warning(
                    f"Product with SKU {parent_sku} not found in inventory, skipping update"
                )
                continue

            # Product update mutation (keep track of product update time on a product level)
            mutation = f"""
                    product_update_{idx + 1}: productUpdate(
                        product: {{
                            id: "{inventory_item["parent_id"]}",
                            metafields: [
                                {{
                                    namespace: "whpm",
                                    key: "update_time",
                                    value: "{update_time}",
                                }}
                            ],
                        }}
                    ) {{
                        userErrors {{
                            field
                            message
                        }}
                    }}"""
            mutation_items.append(mutation)

            # Loop through all variants of the product
            productVariantsBulkUpdate: list[str] = []

            for var_idx, variant_inventory_item in enumerate(
                inventory_item["variants"]
            ):
                variant = [
                    var
                    for var in product.variants
                    if var.sku == variant_inventory_item["sku"]
                ]

                if not variant or len(variant) != 1:
                    self.logger.warning(
                        f"Variant with SKU {variant_inventory_item['sku']} not found in supplier data, skipping update"
                    )
                    continue

                variant = variant[0]

                stock_location = variant_inventory_item.get("stock", {}).get(
                    supplier_name
                )
                if stock_location is None:
                    self.logger.warning(
                        f"Stock information for supplier {supplier_name} not found for variant with SKU {variant_inventory_item['sku']}, skipping update"
                    )
                    continue

                # Add variant information to list of productVariantsBulkUpdate
                productVariantsBulkUpdate.append(f"""
                            {{
                                id: "{variant_inventory_item["variant_id"]}",
                                price: "{variant.price}",
                                inventoryItem: {{
                                    cost: "{variant.cost}",
                                }},
                                metafields: [
                                    {{
                                        namespace: "whpm",
                                        key: "update_time",
                                        value: "{update_time}",
                                    }},
                                ],
                            }},""")

                # Add mutation to update the stock quantity. Updating quantities is not allowed in productVariantsBulkUpdate
                idempotent_key = str(uuid4())
                mutation = f"""
                    product_variant_stock_{idx + 1}_{var_idx + 1}: inventorySetOnHandQuantities(
                        input: {{
                            reason: "correction",
                            setQuantities: [
                                {{
                                    inventoryItemId: "{variant_inventory_item["inventory_id"]}",
                                    locationId: "{stock_location["location_id"]}",
                                    quantity: {variant.stock},
                                }},
                            ],
                        }},
                    ) @idempotent(key: "{idempotent_key}") {{
                        userErrors {{
                            field
                            message
                        }}
                    }}"""
                mutation_items.append(mutation)

            # Create productVariantsBulkUpdate mutation
            if len(productVariantsBulkUpdate) > 0:
                mutation = f"""
                    product_bulk_update_{idx + 1}: productVariantsBulkUpdate(
                        allowPartialUpdates: true,
                        productId: "{inventory_item["parent_id"]}",
                        variants: [
                            {chr(10).join(productVariantsBulkUpdate)}
                        ],
                    ) {{
                        userErrors {{
                            field
                            message
                        }}
                    }}"""
                mutation_items.append(mutation)

        return mutation_items
