"""
Shopify GraphQL API client
Handles all communication with Shopify's GraphQL API
"""

from pathlib import Path
from typing import Any, Optional

import httpx

from wh_product_manager.api.global_funcs import get_request_headers
from wh_product_manager.core.logger import Logger
from wh_product_manager.settings import Settings
from wh_product_manager.shopify.authentication import ShopifyAuthenticationClient


class ShopifyGraphQLClient:
    """GraphQL client for Shopify API"""

    def __init__(
        self,
        settings: Settings,
        logger: Logger,
        authentication_client: ShopifyAuthenticationClient,
    ):
        """
        Initialize Shopify GraphQL client

        Args:
            settings: Application settings containing Shopify credentials
            logger: Logger instance for logging API calls
            authentication_client: Client for handling Shopify authentication
        """
        self.settings = settings
        self.logger = logger
        self.authentication_client = authentication_client

        self.logger.info("ShopifyGraphQLClient initialized")

    async def run(
        self,
        query_string: str,
        store_id: Optional[str] = None,
        variables: Optional[dict[str, Any]] = None,
        enable_timeout: bool = True,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against Shopify API

        Args:
            store_id: Identifier for the Shopify store
            query_string: GraphQL query string
            variables: Optional variables for the GraphQL query
            enable_timeout: Whether to enable a timeout of 30 seconds for the request (default: True)

        Returns:
            dict: GraphQL response data

        Raises:
            httpx.HTTPError: If the API request fails
        """
        if not store_id:
            store_id = await self._get_store_id()

        api_version = await self.authentication_client.get_api_version(store_id)

        access_token = await self.authentication_client.get_access_token(store_id)

        endpoint = (
            f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json"
        )

        self.logger.warning(
            "\n\tStore ID: %s,\n\tAPI Version: %s,\n\tEndpoint: %s,\n\tDecrypted token: %s",
            store_id,
            api_version,
            endpoint,
            access_token,
        )

        try:
            self.logger.debug(
                f"Executing Shopify GraphQL request for {store_id}: "
                f"has_variables={variables is not None}, timeout_enabled={enable_timeout}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "X-Shopify-Access-Token": access_token,
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
                            self.logger.debug("Shopify GraphQL request throttled")
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

    async def post(
        self,
        endpoint: str,
        form_variables: dict[str, str],
        file_path: str | Path,
        file_field_name: str = "file",
        file_content_type: str = "text/jsonl",
        file_name: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        store_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute a multipart/form-data POST request.

        This is primarily used for Shopify staged upload targets where the
        request must contain form variables and a file part.

        Args:
            endpoint: Target URL (for example, a Shopify staged upload URL).
            form_variables: Form fields Shopify returns in staged target parameters.
            file_path: Local file path to upload.
            file_field_name: Multipart field name for the file (default: file).
            file_content_type: Content type of the uploaded file.
            file_name: Optional explicit filename sent in multipart payload.
            headers: Optional additional request headers.
            store_id: Optional store identifier for logging context.

        Returns:
            Parsed JSON response when available, otherwise a metadata dict with
            status and response body text.
        """
        if not store_id:
            store_id = await self._get_store_id()

        try:
            upload_path = Path(file_path)

            if not upload_path.exists() or not upload_path.is_file():
                raise FileNotFoundError(f"Upload file not found: {upload_path}")

            request_headers = dict(headers or {})

            # Let httpx generate multipart boundaries automatically.
            if "Content-Type" in request_headers:
                request_headers.pop("Content-Type")
            if "content-type" in request_headers:
                request_headers.pop("content-type")

            self.logger.debug(
                "Executing multipart Shopify POST request for %s: endpoint=%s, form_fields=%s, file=%s",
                store_id,
                endpoint,
                len(form_variables),
                upload_path,
            )

            async with httpx.AsyncClient() as client:
                with upload_path.open("rb") as file_handle:
                    response = await client.post(
                        endpoint,
                        headers=request_headers,
                        data=form_variables,
                        files={
                            file_field_name: (
                                file_name or upload_path.name,
                                file_handle,
                                file_content_type,
                            )
                        },
                        timeout=30.0,
                    )
                response.raise_for_status()

                response_content_type = response.headers.get("content-type", "")

                if "application/json" in response_content_type.lower():
                    return response.json()

                return {
                    "status_code": response.status_code,
                    "content_type": response_content_type,
                    "text": response.text,
                }

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP request failed: {str(e)}")
            raise ConnectionError(f"HTTP request failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"POST request failed: {str(e)}")
            raise ConnectionError(f"POST request failed: {str(e)}")

    async def _get_store_id(self) -> str:
        request_headers = get_request_headers()
        store_id = request_headers.get("shopify_store_id")

        if store_id is None:
            self.logger.error(
                "Missing 'shopify_store_id'. Pass in either through function 'run' or header in request"
            )
            raise ValueError(
                "Missing 'shopify_store_id'. Pass in either through function 'run' or header in request"
            )

        return store_id
