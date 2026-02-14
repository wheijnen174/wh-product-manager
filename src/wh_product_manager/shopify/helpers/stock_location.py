"""
Shopify helper module for stock location management
Standalone utilities for Shopify API operations
"""

from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient


class StockLocation:
    """
    Helper class for managing Shopify stock locations
    """

    @staticmethod
    async def get_id_by_name(
        location_name: str,
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
    ) -> str:
        """
        Retrieve the Shopify location ID for stock management

        Args:
            location_name: Name of the location to find
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        Returns:
            str: Stock location ID from Shopify

        Raises:
            ValueError: If no stock locations found in Shopify
        """

        query = """
            query ($query: String) {
                locations(first: 100, query: $query) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        """

        try:
            variables: dict[str, Any] = {"query": f"name:{location_name}"}

            response = await shopify_client.query(query, variables)

            locations = response.get("data", {}).get("locations", {}).get("edges", [])

            if not locations:
                logger.error(f"No stock locations found for '{location_name}'.")
                raise ValueError(f"No stock locations found for '{location_name}'.")

            if len(locations) > 1:
                logger.warning(
                    f"Multiple stock locations found for '{location_name}'. Using the first one."
                )

            location_id = locations[0]["node"]["id"]
            location_name = locations[0]["node"]["name"]

            logger.info(f"Using stock location: {location_name}")
            return location_id

        except Exception as e:
            logger.error(f"Failed to retrieve stock location ID: {str(e)}")
            raise
