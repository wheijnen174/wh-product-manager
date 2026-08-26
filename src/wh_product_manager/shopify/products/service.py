from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.shopify.store_authentication import (
    ShopifyStoreAuthentication,
)
from wh_product_manager.db.repositories.products import ProductsRepository
from wh_product_manager.db.repositories.shopify_batch_processes import (
    ShopifyBatchProcessesRepository,
)
from wh_product_manager.db.repositories.shopify_object_assignments import (
    ShopifyObjectAssignmentsRepository,
)
from wh_product_manager.shopify.client import ShopifyGraphQLClient
from wh_product_manager.shopify.products.create import ShopifyProductCreate
from wh_product_manager.shopify.products.delete import ShopifyProductDelete
from wh_product_manager.shopify.products.update import ShopifyProductUpdate


class ShopifyProductService:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
        products_repo: ProductsRepository,
        shopify_object_assignments_repo: ShopifyObjectAssignmentsRepository,
        shopify_batch_processes_repo: ShopifyBatchProcessesRepository,
    ):
        self.shopify_client = shopify_client
        self.logger = logger

        self.products_repo = products_repo
        self.shopify_object_assignments_repo = shopify_object_assignments_repo
        self.shopify_batch_processes_repo = shopify_batch_processes_repo

        self.create = ShopifyProductCreate(
            shopify_client,
            logger,
            products_repo,
            shopify_object_assignments_repo,
            shopify_batch_processes_repo,
        )
        self.update = ShopifyProductUpdate(
            shopify_client, logger, products_repo, shopify_object_assignments_repo
        )
        self.delete = ShopifyProductDelete(
            shopify_client, logger, products_repo, shopify_object_assignments_repo
        )

    async def process_product_upsert(
        self, store: ShopifyStoreAuthentication
    ) -> dict[str, Any]:
        process_results: dict[str, Any] = {}

        products = await self.products_repo.get_products_for_shopify_creation()
        product_assignments = (
            await self.shopify_object_assignments_repo.get_product_assignments_by_store(
                store.id
            )
        )

        flow_separation = await self._separate_products_by_flow(
            products, product_assignments
        )

        process_results["products_created"] = await self.create.create_products(
            store,
            flow_separation["products_to_create"],
        )
        process_results["variants_created"] = await self.create.create_variants(
            store,
            flow_separation["variants_to_create"],
        )

        return process_results

    async def _separate_products_by_flow(
        self, products: dict[int, dict[str, Any]], product_assignments: dict[str, Any]
    ) -> dict[str, list[int]]:

        products_to_create = [
            prod_id
            for prod_id, prod in products.items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id not in product_assignments.get("products", {})
        ]
        products_to_update = [
            prod_id
            for prod_id, prod in products.items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id in product_assignments.get("products", {})
            and product_assignments["products"][prod_id]["is_active"]
        ]
        products_to_activate = [
            prod_id
            for prod_id, prod in products.items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id in product_assignments.get("products", {})
            and not product_assignments["products"][prod_id]["is_active"]
        ]
        products_to_deactivate = [
            prod_id
            for prod_id, prod in products.items()
            if (not prod["is_publishable"] or prod["is_missing"])
            and prod_id in product_assignments.get("products", {})
            and product_assignments["products"][prod_id]["is_active"]
        ]

        # print("Products to create:", products_to_create)
        # print("Products to update:", products_to_update)
        # print("Products to activate:", products_to_activate)
        # print("Products to deactivate:", products_to_deactivate)

        variants_to_create = [
            var_id
            for prod_id, prod in products.items()
            for var_id, var_missing in prod.get("variants", {}).items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id in product_assignments.get("products", {})
            if not var_missing and var_id not in product_assignments.get("variants", {})
        ]
        variants_to_update = [
            var_id
            for prod_id, prod in products.items()
            for var_id, var_missing in prod.get("variants", {}).items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id in product_assignments.get("products", {})
            if not var_missing and var_id in product_assignments.get("variants", {})
        ]
        variants_to_activate = [
            var_id
            for prod_id, prod in products.items()
            for var_id, var_missing in prod.get("variants", {}).items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id in product_assignments.get("products", {})
            if var_missing and var_id in product_assignments.get("variants", {})
        ]
        variants_to_deactivate = [
            var_id
            for prod_id, prod in products.items()
            for var_id, var_missing in prod.get("variants", {}).items()
            if prod["is_publishable"]
            and not prod["is_missing"]
            and prod_id in product_assignments.get("products", {})
            if var_missing and var_id in product_assignments.get("variants", {})
        ]

        # print("Variants to create:", variants_to_create)
        # print("Variants to update:", variants_to_update)
        # print("Variants to activate:", variants_to_activate)
        # print("Variants to deactivate:", variants_to_deactivate)

        return {
            "products_to_create": products_to_create,
            "products_to_update": products_to_update,
            "products_to_activate": products_to_activate,
            "products_to_deactivate": products_to_deactivate,
            "variants_to_create": variants_to_create,
            "variants_to_update": variants_to_update,
            "variants_to_activate": variants_to_activate,
            "variants_to_deactivate": variants_to_deactivate,
        }
