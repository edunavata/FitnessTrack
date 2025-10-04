"""User domain services."""

from __future__ import annotations

from typing import Mapping, TYPE_CHECKING

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
        """Return a placeholder list of users and total count.

        TODO
        ----
        Implement repository-backed filtering and pagination once the database
        layer is connected.
        """

        return self.repo.query(
            self.session,
            filters,
            page=pagination.page,
            limit=pagination.limit,
            sort=pagination.sort,
        )

    def create_user(self, data: Mapping[str, object]):
        """Create a user placeholder until persistence is implemented."""

        # TODO: Persist through SQLAlchemy once migrations are in place.
        return self.repo.create(self.session, data)
