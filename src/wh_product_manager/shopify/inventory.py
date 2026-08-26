"""
Shopify Inventory Service
Retrieves and manages product inventory from Shopify
"""

from asyncio import sleep
from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.settings import Settings
from wh_product_manager.shopify.client import ShopifyGraphQLClient


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

    async def get_current_inventory(
        self, supplier: str | None = None, return_ids: bool = False
    ) -> dict[str, Any]:
        """
        Retrieve current inventory of all Shopify products, optionally filtered by supplier

        Args:
            supplier: Optional supplier name to filter inventory
            return_ids: If True, includes inventory_id, location_id, variant_id in response

        Returns:
            dict: Inventory organized by parent SKU
                {
                    "SKU123": {
                        "parent_id": "gid://shopify/Product/123456789",     # Optional, only included if return_ids=True
                        "parent_status": "ACTIVE",
                        "supplier": "Supplier 1",
                        "parent_last_update": "1900-01-01T00:00:00Z",
                        "variants": [
                            {
                                "inventory_id": "gid://shopify/InventoryItem/123456789",    # Optional, only included if return_ids=True
                                "variant_id": "gid://shopify/ProductVariant/123456789",     # Optional, only included if return_ids=True
                                "sku": "SKU123-RED-M",
                                "last_update": "1900-01-01T00:00:00Z",
                                "cost": 10.0,
                                "price": 19.99,
                                "stock": {
                                    "Location 1": {
                                        "quantity": 0,
                                        "location_id": "gid://shopify/Location/123456789"   # Optional, only included if return_ids=True
                                    },
                                    "Location 2": {
                                        "quantity": 5,
                                        "location_id": "gid://shopify/Location/123456789"   # Optional, only included if return_ids=True
                                    }
                                }
                            }
                        ]
                    }
                }
        """

        self.logger.info(
            "Starting inventory retrieval from Shopify...",
        )

        try:
            query = self._create_graphql_query_inventory()

            cursor = None

            current_inventory: dict[str, Any] = {}

            while True:
                variables: dict[str, Any] = {
                    "batch_size": self.batch_size,
                    "cursor": cursor,
                }

                response = await self.shopify_client.run(query, variables)

                data = response.get("data", {}).get("inventoryItems", {})

                batch_data = data.get("edges", [])

                current_inventory = self._process_inventory_batch(
                    batch_data, current_inventory, supplier, return_ids
                )

                if not data["pageInfo"]["hasNextPage"]:
                    break

                cursor = data["pageInfo"]["endCursor"]

                await sleep(
                    self.settings.SHOPIFY_API_BATCH_DELAY
                )  # Rate limiting delay

            self.logger.info(f"Processed inventory: {len(current_inventory)} products")
            return current_inventory

        except Exception as e:
            self.logger.error(f"Failed to retrieve inventory: {str(e)}")
            raise

    def _create_graphql_query_inventory(self) -> str:
        """
        Create GraphQL query for retrieving inventory data

        Query args:
            batch_size: Number of inventory items to fetch per batch
            cursor: Optional pagination cursor for Shopify API
        Returns:
            str: GraphQL query string
        """

        return """
            query ($batch_size: Int!, $cursor: String) {
                inventoryItems(first: $batch_size, after: $cursor) {
                    edges {
                        cursor
                        node {
                            id
                            sku
                            unitCost {
                                amount
                                currencyCode
                            }
                            inventoryLevels(first: 5) {
                                edges {
                                    node {
                                        location {
                                            id
                                            name
                                        }
                                        quantities(names: "available") {
                                            name
                                            quantity
                                        }
                                    }
                                }
                            }
                            variants(first: 1) {
                                nodes {
                                    id
                                    price
                                    metafield(key: "whpm.update_time") {
                                        value
                                    }
                                    product {
                                        id
                                        status
                                        vendor
                                        metafields(first: 5, keys: ["whpm.head_article_number", "whpm.update_time"]) {
                                            edges {
                                                node {
                                                    key
                                                    value
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        """

    def _process_inventory_batch(
        self,
        batch_data: list[dict[str, Any]],
        current_inventory: dict[str, Any],
        supplier: str | None = None,
        return_ids: bool = True,
    ) -> dict[str, Any]:
        """
        Process a batch of inventory items from Shopify into organized structure

        Args:
            batch_data: List of inventory item edges from Shopify
            current_inventory: Current inventory dictionary to update
            supplier: Optional supplier name to filter inventory
            return_ids: If True, includes inventory_id, location_id, variant_id in response

        Returns:
            dict: Inventory organized by parent SKU
        """

        for edge in batch_data:
            try:
                node = edge["node"]
                variant = node["variants"]["nodes"][0]
                product = variant["product"]
                metafields = product.get("metafields", {}).get("edges", [])

                if node.get("inventoryLevels") is None:
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

                # Skip if supplier filter is set and doesn't match product vendor
                if (
                    supplier is not None
                    and product.get("vendor").lower() != supplier.lower()
                ):
                    continue

                # Initialize parent SKU entry if not exists
                if parent_sku not in current_inventory:
                    current_inventory[parent_sku] = {}

                    if return_ids:
                        current_inventory[parent_sku]["parent_id"] = product["id"]

                    current_inventory[parent_sku]["parent_status"] = product["status"]
                    current_inventory[parent_sku]["supplier"] = product["vendor"]
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
                    variant_data["variant_id"] = variant.get("id", "")

                # Add basic variant info
                variant_data["sku"] = node.get("sku")
                variant_data["last_update"] = (
                    variant.get("metafield", {}).get("value") or None
                )

                # Add cost if valid
                cost = node.get("unitCost", {}).get("amount") or 0
                if self._is_valid_number(cost):
                    variant_data["cost"] = float(cost)

                # Add price if valid
                price = variant.get("price") or 0
                if self._is_valid_number(price):
                    variant_data["price"] = float(price)

                # Add available quantity if valid
                variant_data["stock"] = {}
                stock_locations = node.get("inventoryLevels", {}).get("edges", [])

                for location in stock_locations:
                    location_name = (
                        location.get("node", {}).get("location", {}).get("name", "")
                    )

                    location_id = (
                        location.get("node", {}).get("location", {}).get("id", "")
                    )

                    quantities = location.get("node", {}).get("quantities", [])

                    location_qty = next(
                        (
                            q["quantity"]
                            for q in quantities
                            if q["name"] == "available"
                            and self._is_valid_number(q["quantity"])
                        ),
                        None,
                    )

                    if location_qty is not None:
                        variant_data["stock"][location_name] = {
                            "quantity": int(location_qty)
                        }

                        if return_ids:
                            variant_data["stock"][location_name]["location_id"] = (
                                location_id
                            )

                # Add variant to parent SKU
                current_inventory[parent_sku]["variants"].append(variant_data)

            except (AttributeError, KeyError, TypeError, StopIteration) as e:
                self.logger.error(f"Error processing inventory item: {str(e)}")
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
