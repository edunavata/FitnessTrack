"""Subject domain services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from app.repositories import SubjectRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover
    from app.api.deps import Pagination


class SubjectService:
    """Coordinate subject lifecycle operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = SubjectRepository()

    def list_subjects(self, filters: Mapping[str, object], pagination: Pagination):
        """Return placeholder subjects filtered according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_subject(self, data: Mapping[str, object]):
        """Create a placeholder subject record."""

        # TODO: Persist subjects and handle uniqueness inside the repository.
        return self.repo.create(self.session, data)
