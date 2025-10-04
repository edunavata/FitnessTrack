"""Routine domain services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from app.repositories import RoutineRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover
    from app.api.deps import Pagination


class RoutineService:
    """Coordinate routine lifecycle operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = RoutineRepository()

    def list_routines(self, filters: Mapping[str, object], pagination: Pagination):
        """Return placeholder routines filtered according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_routine(self, data: Mapping[str, object]):
        """Create a placeholder routine record."""

        # TODO: Persist the routine and manage ownership via the repository.
        return self.repo.create(self.session, data)
