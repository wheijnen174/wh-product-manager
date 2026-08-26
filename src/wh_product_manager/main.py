"""
WH Product Manager - Shopify Product Management API
FastAPI application for managing products via Shopify GraphQL API
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from wh_product_manager.api.global_funcs import (
    authenticate_request,
    request_headers_ctx,
)
from wh_product_manager.db.init_db import create_tables
from wh_product_manager.services import Services
from wh_product_manager.settings import Settings

# Global container for dependency injection
services: Services | None = None


def get_services() -> Services:
    """
    Get the global services instance

    Returns:
        Services: The initialized services container

    Raises:
        RuntimeError: If services not yet initialized
    """
    if services is None:
        raise RuntimeError(
            "Services not initialized. Application may not have started yet."
        )
    return services


def create_app(app_settings: Settings) -> FastAPI:
    """
    Factory function to create and configure FastAPI application

    Args:
        app_settings: Application settings

    Returns:
        FastAPI: Configured FastAPI application
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """
        Lifespan context manager for FastAPI
        Handles startup and shutdown events
        """
        global services

        # Startup - create Services with passed settings
        services = Services(app_settings)

        # Create database tables
        await create_tables(services.db_engine)

        try:
            yield
        finally:
            # Shutdown
            if services:
                services.logger.info("Application shutdown")

                await services.aclose()

    app = FastAPI(
        title="WH Product Manager",
        description="Shopify product management via GraphQL API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        dependencies=[
            Depends(authenticate_request),
        ],
    )

    @app.middleware("http")
    async def capture_request_headers(  # pyright: ignore[reportUnusedFunction]
        request: Request, call_next: Any
    ) -> Any:
        token = request_headers_ctx.set(dict(request.headers))
        try:
            return await call_next(request)
        finally:
            request_headers_ctx.reset(token)

    # Only add CORS middleware if enabled
    if app_settings.ENABLE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    # API routes
    from wh_product_manager.api import main_router

    app.include_router(main_router.router, prefix="/api/v1")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all unhandled exceptions globally"""
        try:
            svc = get_services()
            svc.logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        except RuntimeError:
            # Services not initialized yet
            pass

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


# Create the application instance
_settings = Settings()
app = create_app(_settings)


if __name__ == "__main__":
    import uvicorn

    settings = Settings()

    uvicorn.run(
        "wh_product_manager.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL_CONSOLE.lower(),
        reload=settings.DEBUG,
    )
