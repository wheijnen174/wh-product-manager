import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wh_product_manager.config import Settings
from wh_product_manager.services import Services

router = APIRouter()
product_operation_lock = asyncio.Lock()

services = Services(settings=Settings())


@router.get("/inventory")
async def shopify_inventory(return_ids: bool = True) -> JSONResponse:
    """Endpoint to trigger Shopify inventory sync"""
    async with product_operation_lock:
        inventory_data = await services.shopify_inventory.get_current_inventory(
            return_ids
        )

        return JSONResponse(
            status_code=200,
            content=inventory_data,
        )
