from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.models.products.product import ProductORM
from wh_product_manager.db.models.shopify.batch_processes import ShopifyBatchProcessORM
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


class ShopifyProductCreate:
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

    async def create_products(
        self, store: ShopifyStoreAuthentication, product_ids: list[int]
    ) -> int:
        if len(product_ids) == 0:
            self.logger.debug(f"No products to create for store={store.id}")
            return 0

        self.logger.debug(f"Creating products {product_ids} for store={store.id}")

        products = await self.products_repo.get_products_by_ids(
            product_ids, full_detail=True
        )

        # Step 1: fetch all necessary Shopify data for the products to be created
        # (e.g. metafields, collections, etc.) and store in a dict for easy access
        # during mutation construction

        # Step 2: construct the batch mutation for creating all products, using the
        # dict from step 1 to fill in necessary data for each product's mutation body
        all_variables: dict[int, Any] = {}
        for i, product in enumerate(products.values()):
            variables = self._create_mutation__product_set_variables(product, store)

            all_variables[i] = variables

        mutation = self._create_mutation__product_set()

        # Step 3: send batch mutation to database
        batch_mutation = ShopifyBatchProcessORM(
            store_id=store.id,
            operation="create_products",
            status="pending",
            objects_count=len(all_variables),
            query=mutation,
            variables=all_variables,
        )
        await self.shopify_batch_processes_repo.create_batch_process(batch_mutation)

        # Simulate creation logic here
        created_products = {"created_product_ids": product_ids}

        return len(product_ids)

    async def create_variants(
        self, store: ShopifyStoreAuthentication, variant_ids: list[int]
    ) -> int:
        if len(variant_ids) == 0:
            self.logger.debug(f"No variants to create for store={store.id}")
            return 0

        self.logger.debug(f"Creating variants {variant_ids} for store={store.id}")

        # Simulate creation logic here
        created_variants = {"created_variant_ids": variant_ids}

        return len(variant_ids)

    @staticmethod
    def _create_mutation__product_set() -> str:
        """
        Build the GraphQL mutation string for creating a product. Intended for batching multiple product creations into a single batch mutation.

        NOTE: this does not include the mutation wrapper, just the inner part that goes inside the mutation body.
        """

        mutation: str = """
        mutation createProductAsynchronous($productSet: ProductSetInput!) {
            productSet(input: $productSet) {
                product {
                    id
                    variants(first: 50) {
                        nodes {
                            id
                            sku
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }"""

        for _ in range(0, 100):
            mutation = mutation.replace("    ", "  ")

        return mutation

    @staticmethod
    def _create_mutation__product_set_variables(
        product: ProductORM, store: ShopifyStoreAuthentication
    ) -> dict[str, Any]:

        inventory_location_id = store.get_extra_data().get("inventory_location_id")
        if inventory_location_id is None:
            raise ValueError(
                f"Missing inventory_location_id in store.extra_data for store={store.id}"
            )

        titles = {item.source: item.value for item in product.title}
        product_title = titles.get("generated", titles.get("supplier"))

        descriptions = {item.source: item.value for item in product.description}
        product_description = descriptions.get(
            "generated", descriptions.get("supplier")
        )

        sizes = [
            var.size_title for var in product.variants if var.size_title is not None
        ]
        if sizes and len(set(sizes)) > 0:
            product_options: list[dict[str, Any]] = [
                {
                    "name": "Size",
                    "position": 1,
                    "values": [{"name": "S"}, {"name": "L"}],
                }
            ]
            option_values = []
        else:
            product_options: list[dict[str, Any]] = [
                {
                    "name": "Title",
                    "values": [{"name": "Default Title"}],
                }
            ]
            option_values = [{"optionName": "Title", "name": "Default Title"}]

        variables: dict[str, Any] = {
            "productSet": {
                "title": product_title,
                "descriptionHtml": product_description,
                "vendor": product.supplier_name or "",
                # "files": [""],
                "productOptions": product_options,
                "variants": [
                    {
                        "optionValues": option_values,
                        "barcode": variant.barcode or "",
                        "inventoryItem": {
                            "cost": variant.cost,
                            "countryCodeOfOrigin": variant.country_of_origin,
                            "harmonizedSystemCode": str(variant.hscode)
                            if variant.hscode is not None
                            else "",
                            "measurement": {
                                "weight": {
                                    "unit": "GRAMS",
                                    "value": variant.weight or 0,
                                },
                            },
                            "requiresShipping": True,
                            "sku": variant.sku,
                            "tracked": True,
                        },
                        "inventoryPolicy": "DENY",
                        "inventoryQuantities": [
                            {
                                "locationId": inventory_location_id,
                                "name": "available",
                                "quantity": variant.stock,
                            }
                        ],
                        "price": variant.price,
                        "sku": variant.sku,
                        "taxable": True,
                    }
                    for variant in product.variants
                ],
            },
        }

        return {
            "product_id": product.id,
            "variant_ids": {variant.sku: variant.id for variant in product.variants},
            "variables": variables,
        }
