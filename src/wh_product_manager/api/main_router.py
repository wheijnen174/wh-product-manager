from fastapi import APIRouter

from wh_product_manager.api.routes import health, products, shopify, suppliers

router = APIRouter()

# Health check endpoint
router.include_router(health.router, prefix="/health")

# Product management endpoints
router.include_router(products.router, prefix="/products")

# Shopify integration endpoints
router.include_router(shopify.router, prefix="/shopify")

# Supplier management endpoints
router.include_router(suppliers.router, prefix="/suppliers")
