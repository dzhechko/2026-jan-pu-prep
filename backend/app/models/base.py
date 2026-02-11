"""Declarative base for all SQLAlchemy ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base.

    All application models inherit from this class so that
    Alembic can auto-discover them via ``Base.metadata``.
    """

    pass
