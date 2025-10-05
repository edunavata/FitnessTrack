"""
Abstract Unit of Work contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class SupportsCommit(Protocol):
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class UnitOfWork(ABC):
    """
    Coordinates a transactional boundary for a use-case.

    Responsibilities:
    - Provide access to repositories bound to the same session/transaction.
    - Commit on success, rollback on error.
    """

    @abstractmethod
    def __enter__(self) -> UnitOfWork: ...
    @abstractmethod
    def __exit__(self, exc_type, exc, tb) -> None: ...
    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...

    # Concrete implementations expose repository attributes such as users, subjects, or exercises.
