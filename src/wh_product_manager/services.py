"""
Dependency injection container
Initializes and manages all services
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from wh_product_manager.config import Settings
from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.collections import CollectionsRepository
from wh_product_manager.db.models.country_mapping import (
    CountryMappingRepository,
)
from wh_product_manager.db.models.shopify_category_taxonomies import (
    ShopifyCategoryTaxonomiesRepository,
)
from wh_product_manager.shopify.categories import CategoriesService
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.inventory import InventoryService
from wh_product_manager.shopify.metafields import MetafieldService
from wh_product_manager.shopify.metaobjects import MetaobjectService
from wh_product_manager.shopify.product_properties import ProductPropertiesService
from wh_product_manager.shopify.products import ProductService
from wh_product_manager.shopify.publishing import PublicationService
from wh_product_manager.suppliers.service import SupplierService


class Services:
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

        self.db_engine: AsyncEngine = create_async_engine(
            settings.get_database_url(),
            echo=getattr(settings, "DB_ECHO", False),
            pool_pre_ping=True,
        )

        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.db_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        # ------------------------------------------------------------------------------
        # DATABASE SERVICES
        # ------------------------------------------------------------------------------
        self.collections_repo = CollectionsRepository(self.session_factory)
        self.country_mapping_repo = CountryMappingRepository(self.session_factory)
        self.shopify_category_taxonomies_repo = ShopifyCategoryTaxonomiesRepository(
            self.session_factory
        )

        # ------------------------------------------------------------------------------
        # SHOPIFY SERVICES
        # ------------------------------------------------------------------------------
        self.shopify_client = ShopifyGraphQLClient(settings, self.logger)

        self.publication_service = PublicationService(self.shopify_client, self.logger)

        self.inventory_service = InventoryService(
            self.shopify_client, self.settings, self.logger
        )

        self.supplier_service = SupplierService(
            self.shopify_client, settings, self.logger, self.country_mapping_repo
        )

        self.categories_service = CategoriesService(
            self.shopify_client,
            settings,
            self.logger,
            self.publication_service,
            self.shopify_category_taxonomies_repo,
            self.collections_repo,
        )

        self.metafield_service = MetafieldService(
            self.shopify_client, settings, self.logger
        )

        self.metaobject_service = MetaobjectService(
            self.shopify_client, settings, self.logger
        )

        self.product_properties_service = ProductPropertiesService(
            self.shopify_client,
            settings,
            self.logger,
            self.metafield_service,
            self.metaobject_service,
        )

        self.product_service = ProductService(
            self.shopify_client,
            self.settings,
            self.logger,
            self.publication_service,
            self.inventory_service,
            self.supplier_service,
            self.categories_service,
            self.product_properties_service,
        )

        self.logger.info("Services Container initialized with all services")

    async def aclose(self) -> None:
        """Gracefully close resources (db, etc.)."""
        # Dispose SQLAlchemy engine (closes pool connections)
        await self.db_engine.dispose()
