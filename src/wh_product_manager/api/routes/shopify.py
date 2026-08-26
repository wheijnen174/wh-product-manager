from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from wh_product_manager.api.global_funcs import get_services, verify_shopify_store_id

router = APIRouter()


# TODO: Placeholder
@router.get("/")
async def status() -> JSONResponse:
    """Status endpoint - API health check"""
    services = get_services()

    services.logger.info("API shopify/ called")
    services.logger.debug("shopify/ is currently a placeholder endpoint")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "status": "WH Product Manager API is running",
            }
        ),
    )


@router.get("/upsert")
async def upsert(
    shopify_store_id: Annotated[str, Depends(verify_shopify_store_id)],
    shopify_api_version: Annotated[str, Header()] = "2026-04",
    shopify_api_batch_delay: Annotated[float, Header()] = 0.0,
) -> JSONResponse:
    """Status endpoint - API health check"""
    services = get_services()
    services.logger.info(
        "API shopify/upsert called for "
        f"store_id {shopify_store_id} "
        f"(api_version={shopify_api_version}, batch_delay={shopify_api_batch_delay})"
    )

    store = await services.shopify_store_authentication.get_store_by_id(
        int(shopify_store_id)
    )

    response = await services.shopify_product_service.process_product_upsert(
        store=store
    )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(response),
    )


# TODO: Placeholder
@router.get("/batches")
async def execute_batches() -> JSONResponse:
    """Status endpoint - API health check"""
    services = get_services()
    services.logger.info("API shopify/batches called")

    batch_results = {}

    # Step 1: refresh all previously executed batch processes
    batch_results[
        "existing_batches"
    ] = await services.shopify_batch_service.update.refresh()

    # Step 2: execute all pending batch processes
    batch_results["new_batches"] = await services.shopify_batch_service.create.execute()

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(batch_results),
    )


# TODO: Placeholder
@router.get("/get_inventory")
async def get_inventory() -> JSONResponse:
    """Status endpoint - API health check"""
    services = get_services()

    services.logger.info("API shopify/get_inventory called")
    services.logger.debug("shopify/get_inventory is currently a placeholder endpoint")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "status": "WH Product Manager API is running",
            }
        ),
    )
