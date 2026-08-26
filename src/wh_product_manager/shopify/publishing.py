from typing import TypedDict

from wh_product_manager.core.logger import Logger
from wh_product_manager.shopify.client import ShopifyGraphQLClient


class PublicationFailure(TypedDict):
    shopify_id: str
    error: str


class PublicationActionResult(TypedDict):
    succeeded_ids: list[str]
    failed: list[PublicationFailure]


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
    ) -> PublicationActionResult:
        self.logger.info(
            f"Starting Shopify publish workflow for objects={len(object_ids)}"
        )
        if len(object_ids) == 0:
            self.logger.info("No objects to publish")
            return PublicationActionResult(succeeded_ids=[], failed=[])

        batch_size = 75  # Shopify allows up to 100, but using 75 to be safe with API limits and response size

        # Fetch publication IDs once and reuse for all objects
        # These are the IDs of all sales channels (Online Store, POS, etc.)
        publication_ids = await self.get_publication_ids()
        publication_ids_input = ",".join(
            [f"""{{publicationId: "{value}"}}""" for value in publication_ids.values()]
        )

        result: PublicationActionResult = PublicationActionResult(
            succeeded_ids=[],
            failed=[],
        )

        for i in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[i : i + batch_size]
            self.logger.debug(
                f"Publishing batch: start_index={i}, batch_size={len(batch_ids)}"
            )

            try:
                mutation = """
                    mutation {
                """

                for x, object_id in enumerate(batch_ids):
                    try:
                        mutation += f"""
                            publishObject_{x + 1}: publishablePublish(
                                id: "{object_id}",
                                input: [{publication_ids_input}]
                            ) {{
                                userErrors {{
                                    field
                                    message
                                }}
                            }}
                        """
                    except Exception as e:
                        self.logger.error(
                            f"Error constructing mutation for object {object_id}: {e}"
                        )

                mutation += """
                    }
                """

                response = await self.shopify_client.run(mutation)

                for x, object_id in enumerate(batch_ids):
                    user_errors = (
                        response.get("data", {})
                        .get(f"publishObject_{x + 1}", {})
                        .get("userErrors", [])
                    )

                    if user_errors:
                        self.logger.error(
                            f"Failed to publish object {object_id}: {user_errors}"
                        )
                        result["failed"].append(
                            {
                                "shopify_id": object_id,
                                "error": str(user_errors),
                            }
                        )
                    else:
                        self.logger.debug(f"Successfully published object {object_id}")
                        result["succeeded_ids"].append(object_id)
            except Exception as e:
                self.logger.error(
                    f"Error publishing batch starting with object {batch_ids[0]}: {e}"
                )
                for object_id in batch_ids:
                    result["failed"].append(
                        {
                            "shopify_id": object_id,
                            "error": str(e),
                        }
                    )

        return result

    async def unpublish_shopify_objects(
        self,
        object_ids: list[str],
    ) -> PublicationActionResult:
        self.logger.info(
            f"Starting Shopify unpublish workflow for objects={len(object_ids)}"
        )
        if len(object_ids) == 0:
            self.logger.info("No objects to unpublish")
            return PublicationActionResult(succeeded_ids=[], failed=[])

        batch_size = 75
        publication_ids = await self.get_publication_ids()
        publication_ids_input = ",".join(
            [f'{{publicationId: "{value}"}}' for value in publication_ids.values()]
        )

        result: PublicationActionResult = PublicationActionResult(
            succeeded_ids=[],
            failed=[],
        )

        for i in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[i : i + batch_size]
            self.logger.debug(
                f"Unpublishing batch: start_index={i}, batch_size={len(batch_ids)}"
            )

            try:
                mutation = """
                    mutation {
                """

                for x, object_id in enumerate(batch_ids):
                    mutation += f"""
                        unpublishObject_{x + 1}: publishableUnpublish(
                            id: \"{object_id}\",
                            input: [{publication_ids_input}]
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

                response = await self.shopify_client.run(mutation)

                for x, object_id in enumerate(batch_ids):
                    user_errors = (
                        response.get("data", {})
                        .get(f"unpublishObject_{x + 1}", {})
                        .get("userErrors", [])
                    )

                    if user_errors:
                        self.logger.error(
                            f"Failed to unpublish object {object_id}: {user_errors}"
                        )
                        result["failed"].append(
                            {
                                "shopify_id": object_id,
                                "error": str(user_errors),
                            }
                        )
                    else:
                        self.logger.debug(
                            f"Successfully unpublished object {object_id}"
                        )
                        result["succeeded_ids"].append(object_id)

            except Exception as e:
                self.logger.error(
                    f"Error unpublishing batch starting with object {batch_ids[0]}: {e}"
                )
                for object_id in batch_ids:
                    result["failed"].append(
                        {
                            "shopify_id": object_id,
                            "error": str(e),
                        }
                    )

        return result

    async def get_publication_ids(self) -> dict[str, str]:
        """
        Fetches publication IDs from Shopify store

        Returns:
            dict[str, str]: Mapping of publication names to their IDs
        """
        self.logger.info("Fetching Shopify publication IDs")

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

        response = await self.shopify_client.run(query)

        publication_ids = (
            response.get("data", {}).get("publications", {}).get("edges", [])
        )

        if len(publication_ids) == 0:
            self.logger.error("No publications found in Shopify store")
            raise ValueError("No publications found in Shopify store")
        else:
            self.logger.debug(
                f"Fetched Shopify publication IDs: count={len(publication_ids)}"
            )
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
