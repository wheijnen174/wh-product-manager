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

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.collections import CollectionsRepository
from wh_product_manager.db.repositories.country_mapping import CountryMappingRepository
from wh_product_manager.db.repositories.products import ProductsRepository
from wh_product_manager.db.repositories.properties import (
    PropertyDomainRepository,
)
from wh_product_manager.db.repositories.shopify_batch_processes import (
    ShopifyBatchProcessesRepository,
)
from wh_product_manager.db.repositories.shopify_category_taxonomies import (
    ShopifyCategoryTaxonomiesRepository,
)
from wh_product_manager.db.repositories.shopify_object_assignments import (
    ShopifyObjectAssignmentsRepository,
)
from wh_product_manager.db.repositories.shopify_store_authentication import (
    ShopifyStoreAuthenticationRepository,
)
from wh_product_manager.products.service import ProductService
from wh_product_manager.settings import Settings
from wh_product_manager.shopify.authentication import ShopifyAuthenticationClient
from wh_product_manager.shopify.batches.service import ShopifyBatchesService
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.service import ShopifyProductService
from wh_product_manager.shopify.publishing import PublicationService
from wh_product_manager.suppliers.service import SupplierService
from wh_product_manager.utils.temp_file_service import TempFileService


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
        self.logger = Logger(
            level_file=settings.LOG_LEVEL_FILE, level_console=settings.LOG_LEVEL_CONSOLE
        )

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

        self.temp_file_service = TempFileService(self.logger)

        # ------------------------------------------------------------------------------
        # DATABASE SERVICES
        # ------------------------------------------------------------------------------
        self.collections_repo = CollectionsRepository(self.session_factory)
        self.country_mapping_repo = CountryMappingRepository(self.session_factory)
        self.products_repo = ProductsRepository(self.session_factory, self.logger)
        self.property_domain_repo = PropertyDomainRepository(
            self.session_factory, self.logger
        )
        self.shopify_batch_processes_repo = ShopifyBatchProcessesRepository(
            self.session_factory, self.logger
        )
        self.shopify_category_taxonomies_repo = ShopifyCategoryTaxonomiesRepository(
            self.session_factory, self.logger
        )
        self.shopify_object_assignments_repo = ShopifyObjectAssignmentsRepository(
            self.session_factory, self.logger
        )
        self.shopify_store_authentication_repo = ShopifyStoreAuthenticationRepository(
            self.session_factory, self.logger
        )

        # ------------------------------------------------------------------------------
        # SHOPIFY SERVICES
        # ------------------------------------------------------------------------------
        self.shopify_store_authentication = ShopifyAuthenticationClient(
            self.shopify_store_authentication_repo
        )

        self.shopify_client = ShopifyGraphQLClient(
            settings, self.logger, self.shopify_store_authentication
        )

        self.publication_service = PublicationService(self.shopify_client, self.logger)

        # self.inventory_service = InventoryService(
        #     self.shopify_client, self.settings, self.logger
        # )

        self.supplier_service = SupplierService(
            self.shopify_client, settings, self.logger, self.country_mapping_repo
        )

        # self.categories_service = CategoriesService(
        #     self.shopify_client,
        #     settings,
        #     self.logger,
        #     self.publication_service,
        #     self.shopify_category_taxonomies_repo,
        #     self.collections_repo,
        # )

        self.product_service = ProductService(
            self.logger,
            self.products_repo,
            self.property_domain_repo,
        )

        self.shopify_product_service = ShopifyProductService(
            self.shopify_client,
            self.logger,
            self.products_repo,
            self.shopify_object_assignments_repo,
            self.shopify_batch_processes_repo,
        )

        self.shopify_batch_service = ShopifyBatchesService(
            self.shopify_client,
            self.logger,
            self.temp_file_service,
            self.products_repo,
            self.shopify_object_assignments_repo,
            self.shopify_batch_processes_repo,
            self.shopify_store_authentication_repo,
        )

        self.logger.info("Services Container initialized with all services")

    async def aclose(self) -> None:
        """Gracefully close resources (db, etc.)."""
        # Dispose SQLAlchemy engine (closes pool connections)
        await self.db_engine.dispose()
