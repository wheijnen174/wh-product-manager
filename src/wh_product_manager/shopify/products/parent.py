"""
Shopify parent product operations
Create, update, and manage parent products
"""

from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.helpers import (
    is_product_stale,
    validate_product_data,
)
from wh_product_manager.shopify.products.mutations import (
    get_create_product_mutation,
    get_disable_product_mutation,
    get_update_product_mutation,
)


class ParentProductManager:
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

    async def create_product(self, product_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new parent product

        Args:
            product_data: Product data to create

        Returns:
            dict: Response from Shopify
        """
        if not validate_product_data(product_data):
            raise ValueError("Product data missing required fields")

        mutation = get_create_product_mutation()
        variables = {"input": product_data}

        try:
            response = await self.shopify_client.query(mutation, variables)
            if "errors" in response:
                self.logger.error(f"Failed to create product: {response['errors']}")
                raise ValueError(f"GraphQL error: {response['errors']}")

            return response["data"]["productCreate"]

        except Exception as e:
            self.logger.error(f"Error creating product: {str(e)}")
            raise

    async def update_product(
        self, product_id: str, product_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update an existing parent product

        Args:
            product_id: Shopify product ID
            product_data: Updated product data

        Returns:
            dict: Response from Shopify
        """
        mutation = get_update_product_mutation()
        product_data["id"] = product_id
        variables = {"input": product_data}

        try:
            response = await self.shopify_client.query(mutation, variables)
            if "errors" in response:
                self.logger.error(f"Failed to update product: {response['errors']}")
                raise ValueError(f"GraphQL error: {response['errors']}")

            return response["data"]["productUpdate"]

        except Exception as e:
            self.logger.error(f"Error updating product: {str(e)}")
            raise

    async def disable_product(self, product_id: str) -> dict[str, Any]:
        """
        Disable a product by setting status to ARCHIVED

        Args:
            product_id: Shopify product ID

        Returns:
            dict: Response from Shopify
        """
        mutation = get_disable_product_mutation()
        variables = {
            "input": {
                "id": product_id,
                "status": "ARCHIVED",
            }
        }

        try:
            response = await self.shopify_client.query(mutation, variables)
            if "errors" in response:
                self.logger.error(f"Failed to disable product: {response['errors']}")
                raise ValueError(f"GraphQL error: {response['errors']}")

            return response["data"]["productUpdate"]

        except Exception as e:
            self.logger.error(f"Error disabling product: {str(e)}")
            raise

    async def disable_stale_products(
        self, products: list[dict[str, Any]], grace_period_days: int
    ) -> dict[str, Any]:
        """
        Disable all products that are stale (last update older than grace period)

        Args:
            products: List of product dictionaries
            grace_period_days: Number of days allowed since last update

        Returns:
            dict: Summary of disabled products
        """
        disabled_count = 0
        failed_count = 0

        for product in products:
            try:
                last_update = product.get("parent_last_update")
                product_id = product["parent_id"]

                if last_update and is_product_stale(last_update, grace_period_days):
                    await self.disable_product(product_id)
                    disabled_count += 1
                    self.logger.info(f"Disabled stale product: {product_id}")

            except Exception as e:
                failed_count += 1
                self.logger.error(f"Failed to disable product: {str(e)}")
                continue

        return {
            "disabled": disabled_count,
            "failed": failed_count,
            "total": len(products),
        }
