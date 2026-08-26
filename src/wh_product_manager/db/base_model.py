"""
SQLAlchemy declarative base for ORM models.

All ORM models should inherit from `Base` so they share the same metadata.
This metadata is used for migrations (Alembic) and for table creation in dev/test.
"""

from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import NO_VALUE, DeclarativeBase

# def same_as(column_name: str) -> Callable[[Any], Any]:
#     def default_function(context: Any) -> Any:
#         return context.current_parameters.get(column_name)

#     return default_function


class Base(DeclarativeBase):
    def _loaded_collection(self, attr_name: str) -> list[Any]:
        loaded_value = inspect(self).attrs[attr_name].loaded_value
        if loaded_value is NO_VALUE:
            return []

        return list(loaded_value or [])
