from typing import Any

from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.products import ProductsRepository
from wh_product_manager.db.repositories.properties import PropertyDomainRepository
from wh_product_manager.properties.service import PropertyService
from wh_product_manager.suppliers.base import BaseSupplier


class ProductService:
    def __init__(
        self,
        logger: Logger,
        products_repo: ProductsRepository,
        property_domain_repo: PropertyDomainRepository,
    ):
        self.logger = logger
        self.products_repo = products_repo
        self.property_service = PropertyService(logger, property_domain_repo)

    async def upsert_supplier_products(self, supplier: BaseSupplier) -> dict[str, Any]:
        """
        Upsert products for a given supplier

        Workflow steps:
            1. Fetch product data from supplier in unified format
            2. Prepare necessary properties based on supplier data
            3. Upsert property definitions and values to DB and retrieve mappable property info
            4. Attach resolved property mappings to products
            5. Upsert products and variants to DB
            6. Create property assignments to DB
        """

        self.logger.info(
            f"{supplier.name} - Starting upsert of supplier products in ProductService"
        )

        # Step 1: Fetch product data from supplier in unified format
        products = await supplier.get_unified_data()

        # Step 2: Prepare necessary properties based on supplier data
        necessary_properties = (
            await self.property_service.prepare_data.process_properties(products)
        )

        # Step 3: Upsert property definitions and values to DB and retrieve mappable property info
        property_upsert_result = await self.property_service.property_domain_repo.create_definitions_and_values(
            necessary_properties
        )

        # Step 4: Upsert products and variants to DB
        (
            product_upsert_result,
            created_products,
        ) = await self.products_repo.upsert_products_and_variants(products)

        # Step 5: Create property assignments to DB for new products
        property_assignment_result = (
            await self.property_service.property_domain_repo.create_assignments(
                products, created_products
            )
        )  # TODO!

        return {
            "product_upsert_result": product_upsert_result,
            "property_upsert_result": property_upsert_result,
            "property_assignment_result": property_assignment_result,
        }
