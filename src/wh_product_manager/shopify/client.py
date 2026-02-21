"""
Shopify GraphQL API client
Handles all communication with Shopify's GraphQL API
"""

from typing import Any

import httpx

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger


class ShopifyGraphQLClient:
    """GraphQL client for Shopify API"""

    def __init__(self, settings: Settings, logger: Logger):
        """
        Initialize Shopify GraphQL client

        Args:
            settings: Application settings containing Shopify credentials
            logger: Logger instance for logging API calls
        """
        self.settings = settings
        self.logger = logger

        # Build endpoint from settings
        self.endpoint = (
            f"https://"
            f"{settings.SHOPIFY_SHOP_URL}/admin/api/"
            f"{settings.SHOPIFY_API_VERSION}/graphql.json"
        )

        self.logger.info(
            f"ShopifyGraphQLClient initialized for {settings.SHOPIFY_SHOP_URL}"
        )

    async def run(
        self,
        query_string: str,
        variables: dict[str, Any] | None = None,
        enable_timeout: bool = True,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against Shopify API

        Args:
            query_string: GraphQL query string
            variables: Optional variables for the GraphQL query
            enable_timeout: Whether to enable a timeout of 30 seconds for the request (default: True)

        Returns:
            dict: GraphQL response data

        Raises:
            httpx.HTTPError: If the API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    headers={
                        "X-Shopify-Access-Token": self.settings.SHOPIFY_ACCESS_TOKEN,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query_string,
                        "variables": variables or {},
                    },
                    timeout=30.0 if enable_timeout else None,
                )
                response.raise_for_status()

                data = response.json()

                # Check for GraphQL errors
                if "errors" in data and data["errors"]:
                    for error in data["errors"]:
                        code = error.get("extensions", {}).get("code")
                        if code == "THROTTLED":
                            return data

                    self.logger.error(f"GraphQL errors: {data['errors']}")
                    raise ValueError(f"GraphQL query failed: {data['errors']}")

                return data

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP request failed: {str(e)}")
            raise ConnectionError(f"HTTP request failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"GraphQL query failed: {str(e)}")
            raise ConnectionError(f"GraphQL query failed: {str(e)}")
