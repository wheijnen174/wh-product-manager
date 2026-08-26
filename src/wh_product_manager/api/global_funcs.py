from contextvars import ContextVar
from typing import Annotated

from fastapi import Header, HTTPException, Request


def get_services():
    """Helper to get services from main module"""
    from wh_product_manager import main

    if main.services is None:
        raise RuntimeError("Services not initialized")
    return main.services


request_headers_ctx: ContextVar[dict[str, str] | None] = ContextVar(
    "request_headers_ctx", default=None
)


def get_request_headers() -> dict[str, str]:
    return request_headers_ctx.get() or {}


async def authenticate_request(request: Request) -> None:
    """
    Authenticate incoming API request using API key.

    Args:
        request (Request): The incoming request object.

    Raises:
        HTTPException: If the API key is missing or invalid, a 401 Unauthorized error is raised.
    """

    services = get_services()
    settings = services.settings

    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = auth_header.split("Bearer ")[1]
    expected_token = settings.WHPM_API_KEY

    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def verify_supplier_exists(
    supplier: Annotated[str, Header()],
) -> str:
    """
    Verify if a supplier exists.

    Args:
        supplier (str): The supplier name from the request header.

    Returns:
        str: The supplier name if it exists.
    """

    services = get_services()

    supplier_exists = await services.supplier_service.supplier_exists(supplier)

    if not supplier_exists:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier '{supplier}' not found",
        )

    return supplier


async def verify_shopify_store_id(
    shopify_store_id: Annotated[str, Header()],
) -> int:
    """
    Verify if a Shopify store ID exists.

    Args:
        shopify_store_id (str): The Shopify store ID from the request header.

    Returns:
        int: The Shopify store ID if it exists.
    """

    services = get_services()

    store_info = await services.shopify_store_authentication_repo.get_store_by_name(
        shopify_store_id
    )

    if not store_info:
        raise HTTPException(
            status_code=404,
            detail=f"Store with name '{shopify_store_id}' not found",
        )

    return store_info["store_id"]
