"""
Shopify product variant operations
Create, update, and manage product variants
"""

from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.helpers import validate_variant_data
from wh_product_manager.shopify.products.mutations import (
    get_create_variant_mutation,
    get_reorder_variants_mutation,
    get_update_variant_mutation,
)


class VariantProductManager:
    """Manages product variant operations"""

    def __init__(self, shopify_client: ShopifyGraphQLClient, logger: Logger):
        """
        Initialize variant product manager

        Args:
            shopify_client: ShopifyGraphQLClient instance
            logger: Logger instance
        """
        self.shopify_client = shopify_client
        self.logger = logger

    async def create_variant(
        self, product_id: str, variant_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a new product variant

        Args:
            product_id: Shopify product ID
            variant_data: Variant data to create

        Returns:
            dict: Response from Shopify
        """
        if not validate_variant_data(variant_data):
            raise ValueError("Variant data missing required fields")

        mutation = get_create_variant_mutation()
        variant_data["productId"] = product_id
        variables = {"input": variant_data}

        try:
            response = await self.shopify_client.query(mutation, variables)
            if "errors" in response:
                self.logger.error(f"Failed to create variant: {response['errors']}")
                raise ValueError(f"GraphQL error: {response['errors']}")

            return response["data"]["productVariantCreate"]

        except Exception as e:
            self.logger.error(f"Error creating variant: {str(e)}")
            raise

    async def update_variant(
        self, variant_id: str, variant_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update an existing product variant

        Args:
            variant_id: Shopify variant ID
            variant_data: Updated variant data

        Returns:
            dict: Response from Shopify
        """
        mutation = get_update_variant_mutation()
        variant_data["id"] = variant_id
        variables = {"input": variant_data}

        try:
            response = await self.shopify_client.query(mutation, variables)
            if "errors" in response:
                self.logger.error(f"Failed to update variant: {response['errors']}")
                raise ValueError(f"GraphQL error: {response['errors']}")

            return response["data"]["productVariantUpdate"]

        except Exception as e:
            self.logger.error(f"Error updating variant: {str(e)}")
            raise

    async def reorder_variants(
        self, product_id: str, variant_ids: list[str]
    ) -> dict[str, Any]:
        """
        Reorder variants within a product

        Args:
            product_id: Shopify product ID
            variant_ids: List of variant IDs in desired order

        Returns:
            dict: Response from Shopify
        """
        mutation = get_reorder_variants_mutation()
        variables: dict[str, Any] = {
            "productId": product_id,
            "variantIds": variant_ids,
        }

        try:
            response = await self.shopify_client.query(mutation, variables)
            if "errors" in response:
                self.logger.error(f"Failed to reorder variants: {response['errors']}")
                raise ValueError(f"GraphQL error: {response['errors']}")

            return response["data"]["productVariantsReorder"]

        except Exception as e:
            self.logger.error(f"Error reordering variants: {str(e)}")
            raise
