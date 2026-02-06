"""
Application configuration and settings
Loads from environment variables and external files
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # FastAPI
    HOST: str = "localhost"
    PORT: int = 6969
    DEBUG: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS (only needed if you have a web frontend)
    ENABLE_CORS: bool = False
    CORS_ORIGINS: list[str] = []

    # Shopify
    SHOPIFY_SHOP_URL: str = ""
    SHOPIFY_API_VERSION: str = "2026-01"
    SHOPIFY_ACCESS_TOKEN: str = ""
    SHOPIFY_API_BATCH_DELAY: float = 0.0

    # Email/Debugging
    DEBUGGING_SMTP_SERVER: str = ""
    DEBUGGING_SMTP_PORT: int = 465
    DEBUGGING_USERNAME: str = ""
    DEBUGGING_PASSWORD: str = ""
    DEBUGGING_TO_ADDRESS: str = ""

    # WordPress Integration
    WORDPRESS_SHARED_SECRET: str = ""
    WORDPRESS_SEARCH_API_KEY: str = ""

    # Product Settings
    PRODUCT_GRACE_PERIOD_IN_DAYS: int = 7
    ONEDC_XML_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **data):
        """
        Initialize settings and load Shopify token from file
        """
        super().__init__(**data)

        # Load Shopify token from file if it exists
        token_file = Path(".env.shopify-token")
        if token_file.exists():
            self.SHOPIFY_ACCESS_TOKEN = token_file.read_text(encoding="utf-8").strip()
        elif not self.SHOPIFY_ACCESS_TOKEN:
            # Fallback to env var if file doesn't exist
            raise ValueError(
                "SHOPIFY_ACCESS_TOKEN must be either in '.env.shopify-token' file "
                "or in .env file as SHOPIFY_ACCESS_TOKEN"
            )
