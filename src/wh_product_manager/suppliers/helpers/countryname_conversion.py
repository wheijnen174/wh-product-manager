"""
Suppliers helpers module
"""

from wh_product_manager.core.logger import Logger
from wh_product_manager.main import get_services
from wh_product_manager.utils.formatters import normalize_string


class CountrynameConversion:
    """
    Helper class for converting country names to ISO codes
    """

    @staticmethod
    async def map_name_to_iso(
        logger: Logger, input_lang: str | None = None
    ) -> dict[str, str]:
        """
        Prepare a mapping of country names to ISO codes for a specific input language or all languages combined.

        Args:
            logger: Logger instance for logging
            input_lang: Optional language code to filter country names (e.g., 'en', 'fr'). If None, includes all languages.

        Returns:
            dict[str, str]: Mapping of country names (lowercased) to their corresponding ISO codes (lowercased)
        """

        if input_lang is None:
            logger.debug(
                "Preparing country conversion map 'name_to_iso' for all languages combined."
            )
        else:
            logger.debug(
                f"Preparing country conversion map 'name_to_iso' for input language '{input_lang}'."
            )

        services = get_services()
        name = await services.country_mapping_repo.get_name("AD", "en")

        print(name)
        raise NotImplementedError("This method is not implemented yet.")

        prepared_map: dict[str, str] = {}

        for code, values in conversion_map.items():
            for name in values.values():
                names: list[str] = []
                if isinstance(name, str):
                    names = [name]
                else:
                    names = [str(n) for n in name]

                for item in names:
                    if item.lower() not in prepared_map.keys():
                        prepared_map[item.lower()] = code.lower()

                    normalized_name = normalize_string(item.lower()).lower()
                    if (
                        normalized_name != item.lower()
                        and normalized_name not in prepared_map.keys()
                    ):
                        prepared_map[normalized_name] = code.lower()

        return prepared_map

    @staticmethod
    async def map_iso_to_name(logger: Logger, input_lang: str) -> dict[str, str]:
        """
        Prepare a mapping of ISO codes to country names for a specific input language.

        Args:
            logger: Logger instance for logging
            input_lang: Language code to filter country names (e.g., 'en', 'fr')

        Returns:
            dict[str, str]: Mapping of ISO codes (lowercased) to their corresponding country names
        """

        logger.debug(
            f"Preparing country conversion map 'iso_to_name' for input language '{input_lang}'."
        )

        services = get_services()
        name = await services.country_mapping_repo.get_name("AD", "en")

        print(name)
        raise NotImplementedError("This method is not implemented yet.")

        prepared_map: dict[str, str | list[str]] = {
            code.lower(): values.get(input_lang, "")
            for code, values in conversion_map.items()
        }

        prepared_map = {
            code.lower(): str(values) if isinstance(values, str) else str(values[0])
            for code, values in prepared_map.items()
        }

        return prepared_map  # type: ignore
