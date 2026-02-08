"""
Dependency injection container
Initializes and manages all services
"""

from .config import Settings
from .core.logger import Logger


class Container:
    """
    Dependency injection container for all services
    Instantiates all managers and helpers
    """

    def __init__(self, settings: Settings):
        """
        Initialize the container with all dependencies

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = Logger(level=settings.LOG_LEVEL)

        self.logger.info("Container initialized with all services")
