"""
Shopify helper functions
Standalone utilities for Shopify API operations
"""

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient


async def get_stock_location_id(
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
        str: Location ID from Shopify

    Raises:
        ValueError: If no locations found in Shopify
    """

    query = f"""
        query {{
            locations(first: 100, query: "name:{location_name}") {{
                edges {{
                    node {{
                        id
                        name
                    }}
                }}
            }}
        }}
    """

    try:
        response = await shopify_client.query(query)

        locations = response.get("data", {}).get("locations", {}).get("edges", [])

        if not locations:
            logger.error("Couldn't retrieve stock location ID.")
            raise ValueError("No locations found in Shopify")

        location_id = locations[0]["node"]["id"]
        location_name = locations[0]["node"]["name"]

        logger.info(f"Using location: {location_name}")
        return location_id

    except Exception as e:
        logger.error(f"Failed to retrieve location ID: {str(e)}")
        raise
