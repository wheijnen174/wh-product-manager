"""
Custom exceptions for the application
"""


class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid"""

    pass


class ShopifyError(Exception):
    """Raised when Shopify API returns an error"""

    pass


class ValidationError(Exception):
    """Raised when data validation fails"""

    pass
