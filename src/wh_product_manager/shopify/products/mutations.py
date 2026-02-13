"""
Shopify GraphQL mutations for product operations
Centralized GraphQL queries and mutations for products
"""


def mutation_create_product_parent(mutation_name: str | None = None) -> str:
    """
    GraphQL mutation for creating a parent product

    Query args:
        media: List of media inputs for product images
        product: ProductCreateInput object containing product details

    Args:
        mutation_name: Optional name for the mutation (for batching/debugging)
    Returns:
        str: GraphQL mutation string
    """

    return f"""
        mutation {mutation_name if mutation_name else ""}($media: [CreateMediaInput!], $product: ProductCreateInput) {{
            productCreate(media: $media, product: $product) {{
                product {{
                    id
                    title
                    handle
                }}
                userErrors {{
                    field
                    message
                }}
            }}
        }}
    """


def mutation_create_product_set(mutation_name: str | None = None) -> str:
    """
    GraphQL mutation for creating a parent product set

    Query args:
        productSet: ProductSetInput object containing product set details
        synchronous: Boolean indicating if the operation should be synchronous (true) or asynchronous (false)

    Args:
        mutation_name: Optional name for the mutation (for batching/debugging)
    Returns:
        str: GraphQL mutation string
    """

    return f"""
        mutation {mutation_name if mutation_name else ""}($synchronous: Boolean!, $productSet: ProductSetInput!) {{
            productSet(synchronous: $synchronous, input: $productSet) {{
                product {{
                    id
                    variants(first: 100) {{
                        nodes {{
                            id
                        }}
                    }}
                }}
                userErrors {{
                    field
                    message
                }}
            }}
        }}
    """
