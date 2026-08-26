"""
Defines locks for operations that should not be run concurrently.
Functions that need the locks import them from this module and use them as needed.
"""

import asyncio

product_operation_lock = asyncio.Lock()
