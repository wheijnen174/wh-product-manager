"""
SQLAlchemy declarative base for ORM models.

All ORM models should inherit from `Base` so they share the same metadata.
This metadata is used for migrations (Alembic) and for table creation in dev/test.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
