from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wh_product_manager.config import Settings
from wh_product_manager.services import Services

router = APIRouter()

services = Services(settings=Settings())


@router.get("/products")
async def get_all_products() -> JSONResponse:
    """Fetch raw product data from all suppliers"""
    raw_data = await services.supplier_service.fetch_all_data()

    return JSONResponse(
        status_code=200,
        content=raw_data,
    )


@router.get("/{supplier_name}/products")
async def get_supplier_products(supplier_name: str) -> JSONResponse:
    """Fetch raw product data from the specified supplier"""
    try:
        supplier = await services.supplier_service.get_supplier(supplier_name)
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"error": str(e)},
        )

    raw_data = await supplier.fetch_raw_data()

    return JSONResponse(
        status_code=200,
        content=raw_data,
    )
