"""
Shopify parent product operations
Manages creation, updating, and deletion of parent products
"""

from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.mutations import mutation_create_product_parent
from wh_product_manager.suppliers.schemas import UnifiedProduct


class ProductParent:
    """Manages parent product operations"""

    def __init__(self, shopify_client: ShopifyGraphQLClient, logger: Logger):
        """
        Initialize parent product manager

        Args:
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.logger = logger

    async def graphql_mutation__create(self, product: UnifiedProduct) -> dict[str, Any]:
        """Format product data for Shopify GraphQL product creation"""

        product_graphql = product.graphql_variable__create()

        mutation = mutation_create_product_parent()
        variables: dict[str, Any] = {
            "media": product_graphql.get("media", []),
            "product": product_graphql.get("product", {}),
        }

        response = await self.shopify_client.run(mutation, variables)

        return {
            product.title: {
                "mutation": mutation,
                "variables": variables,
                "response": response,
            }
        }
