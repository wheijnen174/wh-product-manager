import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wh_product_manager.config import Settings
from wh_product_manager.services import Services

router = APIRouter()
product_operation_lock = asyncio.Lock()

services = Services(settings=Settings())


@router.get("/inventory")
async def shopify_inventory(
    supplier: str | None = None, return_ids: bool = True
) -> JSONResponse:
    """Endpoint to trigger Shopify inventory sync"""
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
    supplier_exists = await services.supplier_service.supplier_exists(supplier)

    if not supplier_exists:
        return JSONResponse(
            status_code=404,
            content={"error": f"Supplier '{supplier}' not found"},
        )

    async with product_operation_lock:
        result = await services.product_service.create_products_for_supplier(supplier)

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
    supplier_exists = await services.supplier_service.supplier_exists(supplier)

    if not supplier_exists:
        return JSONResponse(
            status_code=404,
            content={"error": f"Supplier '{supplier}' not found"},
        )

    async with product_operation_lock:
        result = await services.product_service.update_products_for_supplier(supplier)

        return JSONResponse(
            status_code=200,
            content={
                "status": f"Supplier '{supplier}' found, product update initiated",
                "result": result,
            },
        )
