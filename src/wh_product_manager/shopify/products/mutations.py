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
