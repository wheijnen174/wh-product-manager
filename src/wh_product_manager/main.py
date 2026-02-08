"""
WH Product Manager - Shopify Product Management API
FastAPI application for managing products via Shopify GraphQL API
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from wh_product_manager.config import Settings
from wh_product_manager.container import Container

# Global container for dependency injection
container: Container | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI
    Handles startup and shutdown events
    """
    global container

    # Startup
    settings = Settings()
    container = Container(settings)
    container.logger.info("Application startup complete")

    yield

    # Shutdown
    if container:
        container.logger.info("Application shutdown")


def create_app() -> FastAPI:
    """
    Factory function to create and configure FastAPI application

    Returns:
        FastAPI: Configured FastAPI application
    """
    settings = Settings()

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
    if settings.ENABLE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    # Include routes
    from wh_product_manager.api.routes import health, products

    app.include_router(health.router, prefix="/api/v1/health")
    app.include_router(products.router, prefix="/api/v1/products")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all unhandled exceptions globally"""
        if container:
            container.logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = Settings()
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )
