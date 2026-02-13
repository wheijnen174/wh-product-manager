"""
WH Product Manager - Shopify Product Management API
FastAPI application for managing products via Shopify GraphQL API
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from wh_product_manager.config import Settings
from wh_product_manager.services import Services

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
        services.logger.info("Application startup complete")

        yield

        # Shutdown
        if services:
            services.logger.info("Application shutdown")

    app = FastAPI(
        title="WH Product Manager",
        description="Shopify product management via GraphQL API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Only add CORS middleware if enabled
    if app_settings.ENABLE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    # ✅ MOVED: Import routes AFTER get_services is defined
    # This prevents circular import issues
    from wh_product_manager.api.routes import health, products, suppliers

    app.include_router(health.router, prefix="/api/v1/health")
    app.include_router(products.router, prefix="/api/v1/products")
    app.include_router(suppliers.router, prefix="/api/v1/suppliers")

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
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )
