"""Unit of Work abstractions and concrete implementations.

This package re-exports the SQLAlchemy-backed unit of work used throughout the
application, alongside the abstract contracts that service layers depend on.
"""

from .base import SupportsCommit, UnitOfWork
from .sqlalchemy_uow import SQLAlchemyReadOnlyUnitOfWork, SQLAlchemyUnitOfWork

__all__ = [
    "SupportsCommit",
    "UnitOfWork",
    "SQLAlchemyUnitOfWork",
    "SQLAlchemyReadOnlyUnitOfWork",
]
