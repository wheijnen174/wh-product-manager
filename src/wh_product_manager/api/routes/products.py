"""Products API routes"""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
product_operation_lock = asyncio.Lock()


def _get_services():
    """Helper to get services (imports locally to avoid circular imports)"""
    from wh_product_manager.main import get_services

    return get_services()


@router.get("/inventory")
async def shopify_inventory(
    supplier: str | None = None, return_ids: bool = True
) -> JSONResponse:
    """Endpoint to trigger Shopify inventory sync"""
    services = _get_services()

    if supplier:
        supplier_exists = await services.supplier_service.supplier_exists(supplier)

        if not supplier_exists:
            return JSONResponse(
                status_code=404,
                content={"error": f"Supplier '{supplier}' not found"},
            )

    async with product_operation_lock:
        inventory_data = await services.shopify_inventory.get_current_inventory(
            supplier=supplier, return_ids=return_ids
        )

        return JSONResponse(
            status_code=200,
            content=inventory_data,
        )


@router.get("/create")
async def create_products(supplier: str) -> JSONResponse:
    """Endpoint to trigger product creation for a supplier"""
    services = _get_services()
    supplier_exists = await services.supplier_service.supplier_exists(supplier)

    if not supplier_exists:
        return JSONResponse(
            status_code=404,
            content={"error": f"Supplier '{supplier}' not found"},
        )

    async with product_operation_lock:
        supplier_obj = await services.supplier_service.get_supplier(supplier)

        result = await services.product_service.create_products_for_supplier(
            supplier_obj
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": f"Supplier '{supplier}' found, product creation initiated",
                "result": result,
            },
        )


@router.get("/update")
async def update_products(supplier: str) -> JSONResponse:
    """Endpoint to trigger product update for a supplier"""
    services = _get_services()
    supplier_exists = await services.supplier_service.supplier_exists(supplier)

    if not supplier_exists:
        return JSONResponse(
            status_code=404,
            content={"error": f"Supplier '{supplier}' not found"},
        )

    async with product_operation_lock:
        supplier_obj = await services.supplier_service.get_supplier(supplier)

        # TODO: Also implement updating of Shopify categories (not collections)!

        result = await services.product_service.update_products_for_supplier(
            supplier_obj
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": f"Supplier '{supplier}' found, product update initiated",
                "result": result,
            },
        )
