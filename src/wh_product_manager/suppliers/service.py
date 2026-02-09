"""
Supplier Data Service
Orchestrates all supplier operations
"""

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger


class SupplierService:
    """
    Service for managing suppliers
    Orchestrates supplier operations
    """

    def __init__(
        self,
        settings: Settings,
        logger: Logger,
    ):
        """
        Initialize supplier service

        Args:
            settings: Application settings
            logger: Logger instance
        """
        self.settings = settings
        self.logger = logger
