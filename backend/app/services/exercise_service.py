"""Exercise domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

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
        """Return placeholder exercises with pagination metadata."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_exercise(self, data: Mapping[str, object]):
        """Create a skeleton exercise representation."""

        # TODO: Persist the exercise and handle conflicts via the repository.
        return self.repo.create(self.session, data)
