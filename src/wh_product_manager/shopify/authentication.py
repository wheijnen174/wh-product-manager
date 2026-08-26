"""
Shopify Authentication client
Handles all authentication aspects with Shopify
"""

from cryptography.fernet import Fernet

from wh_product_manager.api.global_funcs import get_request_headers
from wh_product_manager.db.models.shopify.store_authentication import (
    ShopifyStoreAuthentication,
)
from wh_product_manager.db.repositories.shopify_store_authentication import (
    ShopifyStoreAuthenticationRepository,
)


class ShopifyAuthenticationClient:
    """Authentication client for Shopify API"""

    def __init__(self, store_auth_repo: ShopifyStoreAuthenticationRepository):
        """Initialize Shopify Authentication client"""
        self.store_auth_repo = store_auth_repo

    async def get_store_by_id(self, store_id: int) -> ShopifyStoreAuthentication:
        """
        Get Shopify store authentication details by store ID

        Args:
            store_id: Identifier for the Shopify store
        Returns:
            ShopifyStoreAuthentication: Store authentication details
        """
        return await self.store_auth_repo.get_store_by_id(store_id)

    async def get_access_token(self, store_id: str) -> str:
        """
        Get access token for a given Shopify store

        Args:
            store_id: Identifier for the Shopify store
        Returns:
            Tuple containing the API endpoint and access token for the store
        """

        encoded_token, key = await self.store_auth_repo.get_access_token(store_id)

        cipher_suite = Fernet(key)
        decoded_token = cipher_suite.decrypt(encoded_token).decode("utf-8")

        return decoded_token

    async def get_api_version(self, store_id: str) -> str:
        """
        Get the API version for a given Shopify store

        Args:
            store_id: Identifier for the Shopify store
        Returns:
            str: API version string
        """
        request_headers = get_request_headers()
        api_version = request_headers.get("shopify_api_version")

        if api_version is None:
            return await self.store_auth_repo.get_api_version(store_id)

        return api_version

    async def get_api_batch_delay(self, store_id: str) -> str:
        """
        Get the API batch delay for a given Shopify store

        Args:
            store_id: Identifier for the Shopify store
        Returns:
            str: API batch delay string
        """
        request_headers = get_request_headers()
        api_batch_delay = request_headers.get("shopify_api_batch_delay")

        if api_batch_delay is None:
            return await self.store_auth_repo.get_api_batch_delay(store_id)

        return api_batch_delay
