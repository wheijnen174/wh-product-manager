from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _get_services():
    """Helper to get services from main module"""
    from wh_product_manager import main

    if main.services is None:
        raise RuntimeError("Services not initialized")
    return main.services


@router.get("/")
async def status() -> JSONResponse:
    """Status endpoint - API health check"""
    services = _get_services()

    if not services:
        return JSONResponse(
            status_code=503,
            content={
                "status": "WH Product Manager API is starting up. Services not yet initialized."
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "WH Product Manager API is running",
        },
    )
