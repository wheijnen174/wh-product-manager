"""
Shopify GraphQL mutations for product operations
Centralized GraphQL queries and mutations for products
"""


def get_create_product_mutation() -> str:
    """GraphQL mutation for creating a product parent"""
    return """
        mutation CreateProduct($input: ProductInput!) {
            productCreate(input: $input) {
                product {
                    id
                    title
                    handle
                }
                userErrors {
                    field
                    message
                }
            }
        }
    """


def get_create_variant_mutation() -> str:
    """GraphQL mutation for creating a product variant"""
    return """
        mutation CreateVariant($input: ProductVariantInput!) {
            productVariantCreate(input: $input) {
                productVariant {
                    id
                    sku
                    position
                }
                userErrors {
                    field
                    message
                }
            }
        }
    """


def get_update_product_mutation() -> str:
    """GraphQL mutation for updating a product parent"""
    return """
        mutation UpdateProduct($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    title
                    status
                }
                userErrors {
                    field
                    message
                }
            }
        }
    """


def get_update_variant_mutation() -> str:
    """GraphQL mutation for updating a product variant"""
    return """
        mutation UpdateVariant($input: ProductVariantInput!) {
            productVariantUpdate(input: $input) {
                productVariant {
                    id
                    sku
                }
                userErrors {
                    field
                    message
                }
            }
        }
    """


def get_reorder_variants_mutation() -> str:
    """GraphQL mutation for reordering variants"""
    return """
        mutation ReorderVariants($productId: ID!, $variantIds: [ID!]!) {
            productVariantsReorder(productId: $productId, variantIds: $variantIds) {
                product {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
    """


def get_disable_product_mutation() -> str:
    """GraphQL mutation for disabling a product"""
    return """
        mutation DisableProduct($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    status
                }
                userErrors {
                    field
                    message
                }
            }
        }
    """
