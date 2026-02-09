"""
Product helper functions
Utility functions for product operations
"""

from datetime import datetime, timedelta
from typing import Any


def is_product_stale(last_update: str, grace_period_days: int) -> bool:
    """
    Check if a product is stale (last update is older than grace period)

    Args:
        last_update: ISO format timestamp string
        grace_period_days: Number of days allowed since last update

    Returns:
        bool: True if product is stale
    """
    try:
        last_update_dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
        cutoff_date = datetime.now(last_update_dt.tzinfo) - timedelta(
            days=grace_period_days
        )
        return last_update_dt < cutoff_date
    except (ValueError, TypeError):
        return False


def validate_product_data(product_data: dict[str, Any]) -> bool:
    """
    Validate that product data has required fields

    Args:
        product_data: Product dictionary

    Returns:
        bool: True if valid
    """
    required_fields = ["title", "handle"]
    return all(field in product_data for field in required_fields)


def validate_variant_data(variant_data: dict[str, Any]) -> bool:
    """
    Validate that variant data has required fields

    Args:
        variant_data: Variant dictionary

    Returns:
        bool: True if valid
    """
    required_fields = ["sku", "price"]
    return all(field in variant_data for field in required_fields)
