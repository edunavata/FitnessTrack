"""User domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict
from app.repositories import UserRepository

from . import get_session

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from app.api.deps import Pagination


class UserService:
    """Coordinate user-centric use cases."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.repo = UserRepository()

    def list_users(self, filters: Mapping[str, object], pagination: "Pagination"):
        """Return users filtered and paginated according to request parameters."""

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_user(self, data: Mapping[str, object]):
        """Create a new user and commit the transaction."""

        try:
            user = self.repo.create(self.session, data)
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover - DB dependent
            self.session.rollback()
            raise Conflict("User already exists") from exc
        return user
