import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
product_operation_lock = asyncio.Lock()


@router.get("/")
async def products_root() -> JSONResponse:
    """Root endpoint - API status check"""
    async with product_operation_lock:
        return JSONResponse(
            status_code=200,
            content={
                "status": "WH Product Manager API is running",
                "endpoint": "",
            },
        )
