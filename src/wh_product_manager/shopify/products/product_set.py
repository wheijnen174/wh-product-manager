"""
Shopify product set (parent + variant) operations
Manages creation, updating, and deletion of product sets
"""

from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.mutations import mutation_create_product_set
from wh_product_manager.suppliers.schemas import UnifiedProduct


class ProductSet:
    """Manages product set (parent + variant) operations"""

    def __init__(self, shopify_client: ShopifyGraphQLClient, logger: Logger):
        """
        Initialize product set manager

        Args:
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.logger = logger

    async def graphql_mutation__create(
        self, product: UnifiedProduct, location_id: str
    ) -> dict[str, Any]:
        """Format product data for Shopify GraphQL product creation"""

        product_graphql = product.graphql_variable__create_set(location_id)

        mutation = mutation_create_product_set()
        variables: dict[str, Any] = {
            "synchronous": product_graphql.get("synchronous", []),
            "productSet": product_graphql.get("productSet", {}),
        }

        response = await self.shopify_client.query(mutation, variables)

        product_id = (
            response.get("data", {}).get("productSet", {}).get("product", {}).get("id")
        )
        variant_ids = [
            node.get("id")
            for node in response.get("data", {})
            .get("productSet", {})
            .get("product", {})
            .get("variants", {})
            .get("nodes", [])
        ]

        return {
            product.title: {
                "product_id": product_id,
                "variant_ids": variant_ids,
                # "response": response,
            }
        }
