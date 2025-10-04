"""Workout domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict
from app.repositories import WorkoutRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover
    from app.api.deps import Pagination


class WorkoutService:
    """Coordinate workout session operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = WorkoutRepository()

    def list_workouts(self, filters: Mapping[str, object], pagination: "Pagination"):
        """Return workouts filtered and paginated according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_workout(self, data: Mapping[str, object]):
        """Create a new workout session."""

        try:
            workout = self.repo.create(self.session, data)
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover
            self.session.rollback()
            raise Conflict("Workout already exists") from exc
        return workout
