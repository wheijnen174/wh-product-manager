from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _get_services():
    """Helper to get services from main module"""
    from wh_product_manager import main

    if main.services is None:
        raise RuntimeError("Services not initialized")
    return main.services


@router.get("/products")
async def get_all_products() -> JSONResponse:
    """Fetch raw product data from all suppliers"""
    services = _get_services()
    data = await services.supplier_service.fetch_all_data()

    return JSONResponse(
        status_code=200,
        content={name: data.to_dict() for name, data in data.items()},
    )


@router.get("/{supplier_name}/products")
async def get_supplier_products(supplier_name: str) -> JSONResponse:
    """Fetch raw product data from the specified supplier"""
    services = _get_services()

    try:
        supplier = await services.supplier_service.get_supplier(supplier_name.lower())
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"error": str(e)},
        )

    unified_data = await supplier.get_unified_data()

    return JSONResponse(
        status_code=200,
        content={name: item for name, item in unified_data.to_dict().items()},
    )


@router.get("/{supplier_name}/products/raw")
async def get_supplier_products_raw(supplier_name: str) -> JSONResponse:
    """Fetch raw product data from the specified supplier"""
    services = _get_services()

    try:
        supplier = await services.supplier_service.get_supplier(supplier_name.lower())
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
