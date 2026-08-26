from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from wh_product_manager.api.global_funcs import (
    get_services,
    verify_supplier_exists,
)
from wh_product_manager.api.operation_locks import product_operation_lock

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
    full_detail: Annotated[bool, Header()] = True,
) -> JSONResponse:
    """Get products for a supplier"""
    services = get_services()
    services.logger.info(
        f"API /products/get called for supplier {supplier} (full_detail={full_detail})"
    )

    products = await services.products_repo.get_products_by_supplier(
        supplier, full_detail
    )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "products": products,
            }
        ),
    )


@router.get("/upsert")
async def upsert(
    supplier: Annotated[str, Depends(verify_supplier_exists)],
) -> JSONResponse:
    """Upsert products for a supplier"""
    services = get_services()

    services.logger.info(f"{supplier} - API /products/upsert called for this supplier")

    supplier_object = await services.supplier_service.get_supplier(supplier)

    async with product_operation_lock:
        workflow_summary = await services.product_service.upsert_supplier_products(
            supplier_object
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "summary": workflow_summary,
            }
        ),
    )
