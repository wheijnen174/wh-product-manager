"""
Shopify Inventory Service
Retrieves and manages product inventory from Shopify
"""

from asyncio import sleep
from typing import Any

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.helpers.stock_location import StockLocation


class InventoryService:
    """Service for retrieving and managing Shopify inventory"""

    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        settings: Settings,
        logger: Logger,
    ):
        """
        Initialize inventory service

        Args:
            shopify_client: ShopifyGraphQLClient instance
            settings: Application settings
            logger: Logger instance
        """

        self.shopify_client = shopify_client
        self.settings = settings
        self.logger = logger
        self.batch_size = 250  # Number of inventory items to fetch per batch, 250 is Shopify's max for query

    async def get_current_inventory(self, return_ids: bool = False) -> dict[str, Any]:
        """
        Retrieve current inventory of all Shopify products

        Args:
            return_ids: If True, includes inventory_id, location_id, variant_id in response

        Returns:
            dict: Inventory organized by parent SKU
                {
                    "SKU123": {
                        "parent_id": "gid://shopify/Product/123456789",     # Optional, only included if return_ids=True
                        "parent_status": "active",
                        "parent_last_update": "2024-01-15",
                        "variants": [
                            {
                                "inventory_id": "gid://shopify/InventoryItem/123456789",    # Optional, only included if return_ids=True
                                "location_id": "gid://shopify/Location/123456789",          # Optional, only included if return_ids=True
                                "variant_id": "gid://shopify/ProductVariant/123456789",     # Optional, only included if return_ids=True
                                "sku": "SKU123-RED-M",
                                "last_update": "1900-01-01T00:00:00Z",
                                "cost_per_item": 10.0,
                                "price": 19.99,
                                "available_quantity": 0
                            }
                        ]
                    }
                }
        """

        self.logger.info("Starting inventory retrieval from Shopify...")

        try:
            location_id = await StockLocation.get_id_by_name(
                shopify_client=self.shopify_client,
                logger=self.logger,
                location_name="One-DC",
            )

            query = self._create_graphql_query_inventory(location_id)

            cursor = None

            current_inventory: dict[str, Any] = {}

            while True:
                variables: dict[str, Any] = {
                    "batch_size": self.batch_size,
                    "location_id": location_id,
                    "cursor": cursor,
                }

                response = await self.shopify_client.query(query, variables)

                data = response.get("data", {}).get("inventoryItems", {})

                batch_data = data.get("edges", [])

                current_inventory = self._process_inventory_batch(
                    batch_data, current_inventory, return_ids
                )

                if not data["pageInfo"]["hasNextPage"]:
                    break

                cursor = data["pageInfo"]["endCursor"]

                await sleep(
                    self.settings.SHOPIFY_API_BATCH_DELAY
                )  # Rate limiting delay

            self.logger.info(
                f"Processed inventory: {len(current_inventory)} parent SKUs"
            )
            return current_inventory

        except Exception as e:
            self.logger.error(f"Failed to retrieve inventory: {str(e)}")
            raise

    def _create_graphql_query_inventory(self, location_id: str) -> str:
        """
        Create GraphQL query for retrieving inventory data

        Args:
            cursor: Optional pagination cursor for Shopify API
        Returns:
            str: GraphQL query string
        """

        return f"""
            query ($batch_size: Int!, $cursor: String) {{
                inventoryItems(first: $batch_size, after: $cursor) {{
                    edges {{
                        cursor
                        node {{
                            id
                            sku
                            unitCost {{
                                amount
                                currencyCode
                            }}
                            inventoryLevel(locationId: "{location_id}") {{
                                quantities(names: "available") {{
                                    name
                                    quantity
                                }}
                                location {{
                                    id
                                }}
                            }}
                            variant {{
                                id
                                price
                                metafield(key: "whpm.update_time") {{
                                    value
                                }}
                                product {{
                                    id
                                    status
                                    metafields(first: 5, keys: ["whpm.head_article_number", "whpm.update_time"]) {{
                                        edges {{
                                            node {{
                                                key
                                                value
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                }}
            }}
        """

    def _process_inventory_batch(
        self,
        batch_data: list[dict[str, Any]],
        current_inventory: dict[str, Any],
        return_ids: bool = True,
    ) -> dict[str, Any]:
        """
        Process a batch of inventory items from Shopify into organized structure

        Args:
            batch_data: List of inventory item edges from Shopify
            current_inventory: Current inventory dictionary to update

        Returns:
            dict: Inventory organized by parent SKU
                {
                    "SKU123": {
                        "parent_id": "...",
                        "parent_status": "ACTIVE",
                        "parent_last_update": "...",
                        "variants": [...]
                    }
                }
        """

        for edge in batch_data:
            try:
                node = edge["node"]
                variant = node["variant"]
                product = variant["product"]
                metafields = product.get("metafields", {}).get("edges", [])

                if node.get("inventoryLevel") is None:
                    continue

                # Extract parent SKU from metafields
                parent_sku = next(
                    (
                        m["node"]["value"]
                        for m in metafields
                        if m["node"]["key"] == "whpm.head_article_number"
                    ),
                    None,
                )

                # Skip if no parent SKU found
                if not parent_sku:
                    continue

                # Initialize parent SKU entry if not exists
                if parent_sku not in current_inventory:
                    current_inventory[parent_sku] = {}

                    if return_ids:
                        current_inventory[parent_sku]["parent_id"] = product["id"]

                    current_inventory[parent_sku]["parent_status"] = product["status"]
                    current_inventory[parent_sku]["parent_last_update"] = next(
                        (
                            m["node"]["value"]
                            for m in metafields
                            if m["node"]["key"] == "whpm.update_time"
                        ),
                        None,
                    )
                    current_inventory[parent_sku]["variants"] = []

                # Extract variant data
                variant_data: dict[str, Any] = {}

                # Add IDs if requested
                if return_ids:
                    variant_data["inventory_id"] = node.get("id", "")
                    variant_data["location_id"] = (
                        node.get("inventoryLevel", {}).get("location", {}).get("id", "")
                    )
                    variant_data["variant_id"] = variant.get("id", "")
                # Add basic variant info
                variant_data["sku"] = node.get("sku")
                variant_data["last_update"] = variant.get("metafield", {}).get("value")

                # Add cost if valid
                cost = node.get("unitCost", {}).get("amount")
                if self._is_valid_number(cost):
                    variant_data["cost_per_item"] = float(cost)

                # Add price if valid
                price = variant.get("price")
                if self._is_valid_number(price):
                    variant_data["price"] = float(price)

                # Add available quantity if valid
                quantities = node.get("inventoryLevel", {}).get("quantities", [])
                qty = next(
                    (q["quantity"] for q in quantities if q["name"] == "available"),
                    None,
                )
                if isinstance(qty, int):
                    variant_data["available_quantity"] = qty

                # Add variant to parent SKU
                current_inventory[parent_sku]["variants"].append(variant_data)

            except (KeyError, TypeError, StopIteration) as e:
                self.logger.error(f"Failed to retrieve location ID: {str(e)}")
                continue

        return current_inventory

    def _is_valid_number(self, value: Any) -> bool:
        """
        Check if a value can be converted to a float

        Args:
            value: Value to check

        Returns:
            bool: True if value is a valid number
        """
        if value is None:
            return False

        if isinstance(value, (int, float)):
            return True

        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False

        return False
