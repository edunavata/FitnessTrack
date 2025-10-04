"""Subject domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict
from app.repositories import SubjectRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover
    from app.api.deps import Pagination


class SubjectService:
    """Coordinate subject lifecycle operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = SubjectRepository()

    def list_subjects(self, filters: Mapping[str, object], pagination: "Pagination"):
        """Return subjects filtered and paginated according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_subject(self, data: Mapping[str, object]):
        """Create a new subject record."""

        try:
            subject = self.repo.create(self.session, data)
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover
            self.session.rollback()
            raise Conflict("Subject already exists") from exc
        return subject
