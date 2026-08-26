from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from wh_product_manager.api.global_funcs import get_services

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
