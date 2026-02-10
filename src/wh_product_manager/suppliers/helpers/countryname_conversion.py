"""
Suppliers helpers module
"""

from wh_product_manager.core.logger import Logger
from wh_product_manager.utils.data_loader import load_json
from wh_product_manager.utils.formatters import normalize_string


class CountrynameConversion:
    """
    Helper class for converting country names to ISO codes
    """

    @staticmethod
    def map_name_to_iso(
        logger: Logger, input_lang: str | None = None
    ) -> dict[str, str]:
        if input_lang is None:
            logger.debug(
                "Preparing country conversion map 'name_to_iso' for all languages combined."
            )
        else:
            logger.debug(
                f"Preparing country conversion map 'name_to_iso' for input language '{input_lang}'."
            )

        conversion_map = load_json("country_mappings.json")

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
    def name_to_iso_code(country_name: str, input_lang: str, logger: Logger) -> str:
        """
        Convert a country name to the format expected by ISO codes

        Args:
            country_name: The original country name
            input_lang: The language of the input country name in ISO Code format (e.g., 'nl' for Dutch)
            logger: Logger instance for logging conversion process

        Returns:
            str: The converted country name in ISO code format
        """
        logger.debug(f"Converting country name '{country_name}' to ISO code format.")

        conversion_map = load_json("country_mappings.json")

        conversion_map = {
            values[input_lang.lower()].lower(): code
            for code, values in conversion_map.items()
        }

        print(conversion_map)

        converted_name = conversion_map.get(country_name.lower())

        if not converted_name:
            logger.warning(
                f"No mapping found for country name '{country_name}' with input language '{input_lang.lower()}'. Returning original name."
            )
            converted_name = country_name
        else:
            logger.debug(
                f"Converted country name '{country_name}' to '{converted_name}'."
            )

        return converted_name

    @staticmethod
    def iso_code_to_name(country_code: str, input_lang: str, logger: Logger) -> str:
        """
        Convert a country name from ISO code format back to the original name

        Args:
            country_code: The original country code
            input_lang: The language of the input country name in ISO Code format (e.g., 'nl' for Dutch)
            logger: Logger instance for logging conversion process

        Returns:
            str: The converted country name in original format
        """
        logger.debug(
            f"Converting country '{country_code}' from ISO code format to original name."
        )

        conversion_map = load_json("country_mappings.json")

        converted_name = conversion_map.get(country_code, {}).get(input_lang.lower())

        if not converted_name:
            logger.warning(
                f"No mapping found for country code '{country_code}' with input language '{input_lang.lower()}'. Returning original code."
            )
            converted_name = country_code
        else:
            logger.debug(
                f"Converted country code '{country_code}' to '{converted_name}'."
            )

        return converted_name
