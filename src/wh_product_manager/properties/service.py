from wh_product_manager.core.logger import Logger
from wh_product_manager.db.repositories.properties import PropertyDomainRepository
from wh_product_manager.properties.data_processing import PropertyDataProcessor


class PropertyService:
    def __init__(
        self,
        logger: Logger,
        property_domain_repo: PropertyDomainRepository,
    ):
        self.logger = logger
        self.property_domain_repo = property_domain_repo

        self.prepare_data = PropertyDataProcessor(logger)
