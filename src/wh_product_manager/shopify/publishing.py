from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient


class PublicationService:
    def __init__(
        self,
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
    ):
        self.shopify_client = shopify_client
        self.logger = logger

    async def publish_shopify_objects(
        self,
        object_ids: list[str],
        shopify_client: ShopifyGraphQLClient,
        logger: Logger,
    ) -> None:
        if len(object_ids) == 0:
            logger.info("No objects to publish")
            return

        batch_size = 75  # Shopify allows up to 100, but using 75 to be safe with API limits and response size

        publication_ids = await self.get_publication_ids()
        publication_ids = ",".join(
            [f"""{{publicationId: "{value}"}}""" for value in publication_ids.values()]
        )

        for i in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[i : i + batch_size]

            mutation = """
                mutation {
            """

            for x, object_id in enumerate(batch_ids):
                mutation += f"""
                    publishObject_{x + 1}: publishablePublish(
                        id: "{object_id}",
                        input: [{publication_ids}]
                    ) {{
                        userErrors {{
                            field
                            message
                        }}
                    }}
                """

            mutation += """
                }
            """

            response = await self.shopify_client.query(mutation)
            for x, object_id in enumerate(batch_ids):
                user_errors = (
                    response.get("data", {})
                    .get(f"publishObject_{x + 1}", {})
                    .get("userErrors", [])
                )

                if user_errors:
                    logger.error(f"Failed to publish object {object_id}: {user_errors}")
                else:
                    logger.debug(f"Successfully published object {object_id}")

    async def get_publication_ids(self) -> dict[str, str]:
        """
        Fetches publication IDs from Shopify store

        Returns:
            dict[str, str]: Mapping of publication names to their IDs
        """

        query = """
            query {
                publications(first: 250) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        """

        response = await self.shopify_client.query(query)

        publication_ids = (
            response.get("data", {}).get("publications", {}).get("edges", [])
        )

        if len(publication_ids) == 0:
            self.logger.error("No publications found in Shopify store")
            raise ValueError("No publications found in Shopify store")
        else:
            return {
                item["node"]["name"]: item["node"]["id"] for item in publication_ids
            }

    @staticmethod
    def mutation_publish_shopify_object(mutation_name: str | None = None) -> str:
        """
        GraphQL mutation for publishing a Shopify object (e.g. product, collection)

        Mutation args:
            id: ID of the object to publish
            input: [PublicationInput!]! object containing publish details

        Args:
            mutation_name: Optional name for the mutation (for batching/debugging)
        Returns:
            str: GraphQL mutation string
        """

        return f"""
            mutation {mutation_name if mutation_name else ""}($id: ID!, $input: [PublicationInput!]!) {{
                publishablePublish(id: $id, input: $input) {{
                    userErrors {{
                        field
                        message
                    }}
                }}
            }}
        """
