"""
Various helper functions
"""

import unicodedata


def string_needs_normalization(text: str) -> bool:
    """
    Check if a string contains special characters that need normalization

    Args:
        text: String to check

    Returns:
        bool: True if string contains non-ASCII characters

    Examples:
        >>> string_needs_normalization("italie")
        False
        >>> string_needs_normalization("italië")
        True
        >>> string_needs_normalization("café")
        True
    """
    return not all(ord(char) < 128 for char in text)


def normalize_string(text: str) -> str:
    """
    Convert strings with special characters to ASCII-only strings

    Removes:
    - Accents and diacritics (é → e, ñ → n)
    - Non-ASCII symbols (« → removed, € → removed)

    Only performs normalization if the string contains non-ASCII characters.
    This is optimized for performance - ASCII strings are returned as-is.

    Args:
        text: String with possible special characters

    Returns:
        str: Normalized string with only ASCII characters

    Examples:
        >>> normalize_string("italie")
        'italie'
        >>> normalize_string("italië")
        'italie'
        >>> normalize_string("sao tomé en principe")
        'sao tome en principe'
        >>> normalize_string("café «premium»")
        'cafe premium'
        >>> normalize_string("Price: €50")
        'Price: 50'
    """
    # Skip normalization if already ASCII (performance optimization)
    if text.isascii():
        return text

    # Step 1: Decompose accents (é → e + ´)
    nfd = unicodedata.normalize("NFD", text)

    # Step 2: Remove accent marks
    without_accents = "".join(
        c
        for c in nfd
        if unicodedata.category(c) != "Mn"  # 'Mn' = Mark, Nonspacing
    )

    # Step 3: Remove any remaining non-ASCII characters («, », €, etc.)
    ascii_only = without_accents.encode("ascii", errors="ignore").decode("ascii")

    return ascii_only
