from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.products import ProductsRepository
from wh_product_manager.db.repositories.shopify_batch_processes import (
    ShopifyBatchProcessesRepository,
)
from wh_product_manager.db.repositories.shopify_object_assignments import (
    ShopifyObjectAssignmentsRepository,
)
from wh_product_manager.db.repositories.shopify_store_authentication import (
    ShopifyStoreAuthenticationRepository,
)
from wh_product_manager.shopify.batches.create import ShopifyBatchCreate
from wh_product_manager.shopify.batches.update import ShopifyBatchUpdate
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.utils.temp_file_service import TempFileService


class ShopifyBatchesService:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
        temp_file_service: TempFileService,
        products_repo: ProductsRepository,
        shopify_object_assignments_repo: ShopifyObjectAssignmentsRepository,
        shopify_batch_processes_repo: ShopifyBatchProcessesRepository,
        shopify_store_authentication_repo: ShopifyStoreAuthenticationRepository,
    ):
        self.shopify_client = shopify_client
        self.logger = logger
        self.temp_file_service = temp_file_service

        self.products_repo = products_repo
        self.shopify_object_assignments_repo = shopify_object_assignments_repo
        self.shopify_batch_processes_repo = shopify_batch_processes_repo
        self.shopify_store_authentication_repo = shopify_store_authentication_repo

        self.create = ShopifyBatchCreate(
            shopify_client,
            logger,
            temp_file_service,
            products_repo,
            shopify_object_assignments_repo,
            shopify_batch_processes_repo,
            shopify_store_authentication_repo,
        )

        self.update = ShopifyBatchUpdate(
            shopify_client,
            logger,
            temp_file_service,
            products_repo,
            shopify_object_assignments_repo,
            shopify_batch_processes_repo,
            shopify_store_authentication_repo,
        )
