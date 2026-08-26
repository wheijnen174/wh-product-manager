from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.products import ProductsRepository
from wh_product_manager.db.repositories.shopify_object_assignments import (
    ShopifyObjectAssignmentsRepository,
)
from wh_product_manager.shopify.client import ShopifyGraphQLClient


class ShopifyProductDelete:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
        products_repo: ProductsRepository,
        shopify_object_assignments_repo: ShopifyObjectAssignmentsRepository,
    ):
        self.shopify_client = shopify_client
        self.logger = logger

        self.products_repo = products_repo
        self.shopify_object_assignments_repo = shopify_object_assignments_repo
