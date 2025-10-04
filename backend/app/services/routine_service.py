"""Routine domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict
from app.repositories import RoutineRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover
    from app.api.deps import Pagination


class RoutineService:
    """Coordinate routine lifecycle operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = RoutineRepository()

    def list_routines(self, filters: Mapping[str, object], pagination: "Pagination"):
        """Return routines filtered and paginated according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_routine(self, data: Mapping[str, object]):
        """Create a new routine record."""

        try:
            routine = self.repo.create(self.session, data)
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover
            self.session.rollback()
            raise Conflict("Routine already exists") from exc
        return routine
