"""Exercise domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict
from app.repositories import ExerciseRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover
    from app.api.deps import Pagination


class ExerciseService:
    """Coordinate exercise catalogue operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = ExerciseRepository()

    def list_exercises(self, filters: Mapping[str, object], pagination: "Pagination"):
        """Return exercises filtered and paginated according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_exercise(self, data: Mapping[str, object]):
        """Create a new exercise entry."""

        try:
            exercise = self.repo.create(self.session, data)
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover
            self.session.rollback()
            raise Conflict("Exercise already exists") from exc
        return exercise
