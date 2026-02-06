"""
Startup script for the application
Loads settings from config and starts uvicorn with proper parameters
"""

import uvicorn

from .config import Settings


def main():
    """Start the application server"""
    settings = Settings()

    uvicorn.run(
        "wh_product_manager.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
