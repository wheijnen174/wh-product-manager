from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
async def status() -> JSONResponse:
    """Status endpoint - API health check"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "WH Product Manager API is running",
        },
    )
