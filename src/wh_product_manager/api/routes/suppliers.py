from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from wh_product_manager.api.global_funcs import (
    get_services,
    verify_supplier_exists,
)

router = APIRouter()


@router.get("/")
async def status() -> JSONResponse:
    """Status endpoint - API health check"""
    services = get_services()

    services.logger.debug("Health check endpoint accessed - API is running")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "status": "WH Product Manager API is running",
            }
        ),
    )


@router.get("/get")
async def get(
    supplier: Annotated[str, Depends(verify_supplier_exists)],
) -> JSONResponse:
    """Get inventory data for a specific supplier."""
    services = get_services()
    services.logger.info(f"API suppliers/get called: supplier={supplier}")

    supplier_object = await services.supplier_service.get_supplier(supplier)
    supplier_data = await supplier_object.get_unified_data()
    services.logger.debug(
        f"API suppliers/get completed: supplier={supplier}, products={len(supplier_data.products or {})}"
    )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(supplier_data.to_dict()),
    )
