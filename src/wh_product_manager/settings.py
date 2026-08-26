"""
Application configuration and settings
Loads from environment variables and external files
"""

from pydantic_settings import BaseSettings

from wh_product_manager.utils.data_loader import get_log_file


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # FastAPI
    HOST: str = "localhost"
    PORT: int = 6969
    DEBUG: bool = False

    # Logging
    LOG_LEVEL_CONSOLE: str = "WARNING"
    LOG_LEVEL_FILE: str = "INFO"
    LOG_FILE: str = str(get_log_file())

    # CORS (only needed if you have a web frontend)
    ENABLE_CORS: bool = False
    CORS_ORIGINS: list[str] = []

    # WH Product Manager
    WHPM_API_KEY: str

    # Database
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_ECHO: bool = False

    # Products
    PRODUCT_GRACE_PERIOD_IN_DAYS: int = 7

    # Email/Debugging
    DEBUGGING_SMTP_SERVER: str = ""
    DEBUGGING_SMTP_PORT: int = 465
    DEBUGGING_USERNAME: str = ""
    DEBUGGING_PASSWORD: str = ""
    DEBUGGING_TO_ADDRESS: str = ""

    # WordPress Integration
    WORDPRESS_SHARED_SECRET: str = ""
    WORDPRESS_SEARCH_API_KEY: str = ""

    ONEDC_XML_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Construct the database URL from individual components"""
        return f"mysql+asyncmy://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
