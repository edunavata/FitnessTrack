"""User repository for persistence and authentication utilities."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select

from app.models.user import User
from app.repositories import base as base_module
from app.repositories.base import BaseRepository

# Re-exported for tests expecting a public alias
apply_sorting = base_module._apply_sorting


class UserRepository(BaseRepository[User]):
    """Persistence-only repository for :class:`User`.

    This repository focuses on safe lookup, filtering, and password operations.
    It NEVER handles JWT or session creation — only DB-level user management.
    """

    model = User

    # ---------------------------- Whitelists ----------------------------

    def _sortable_fields(self):
        """Expose sortable fields for safe public sorting."""
        return {
            "id": User.id,
            "email": User.email,
            "username": User.username,
            "created_at": User.created_at,
        }

    def _filterable_fields(self):
        """Whitelist fields safe for equality filters."""
        return {
            "email": User.email,
            "username": User.username,
        }

    def _updatable_fields(self):
        """Publicly allowed updatable fields (not including password)."""
        return {"email", "username", "full_name"}

    # ---------------------------- Lookup helpers ----------------------------

    def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email (case-insensitive).

        :param email: Email address to normalise and search.
        :type email: str
        :returns: User instance or ``None`` when not found.
        :rtype: User | None
        """
        stmt = select(User).where(User.email == email.lower().strip())
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(User | None, result)

    def exists_by_email(self, email: str) -> bool:
        """Return ``True`` when a user with the provided email exists.

        :param email: Email address to normalise and search.
        :type email: str
        :returns: ``True`` if a row is found; otherwise ``False``.
        :rtype: bool
        """
        stmt = select(User.id).where(User.email == email.lower().strip())
        return bool(self.session.execute(stmt).first())

    # ---------------------------- Password ops ----------------------------

    def update_password(self, user_id: int, new_password: str) -> None:
        """Update a user's password and flush the session.

        :param user_id: Identifier of the user.
        :type user_id: int
        :param new_password: Raw password to assign; model handles hashing.
        :type new_password: str
        :raises ValueError: If the user does not exist.
        """
        user = self.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        user.password = new_password  # invokes setter → hash
        self.flush()

    def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate a user by email and password.

        :param email: Email address to authenticate.
        :type email: str
        :param password: Raw password to verify.
        :type password: str
        :returns: Authenticated user or ``None`` when credentials fail.
        :rtype: User | None
        """
        user = self.get_by_email(email)
        if not user or not user.verify_password(password):
            return None
        return user

    # ---------------------------- Eager loading ----------------------------

    def _default_eagerload(self, stmt):
        """Return the statement unchanged as no eager loading is required.

        :param stmt: ``SELECT`` statement to potentially augment.
        :type stmt: :class:`sqlalchemy.sql.Select`
        :returns: The same statement without modification.
        :rtype: :class:`sqlalchemy.sql.Select`
        """
        return stmt

    # ---------------------------- JWT ----------------------------

    def get_token_version(self, user_id: int) -> int:
        """
        Return current token_version for the given user.
        """
        return int(self.session.query(User.token_version).filter(User.id == user_id).scalar_one())

    def bump_token_version(self, user_id: int) -> int:
        """
        Atomically increment token_version.

        :returns: New token_version after increment.
        """
        # Use a single UPDATE to avoid race conditions.
        # RETURNING requires PG; for SQLite tests, re-read after update.
        q = (
            self.session.query(User)
            .filter(User.id == user_id)
            .with_for_update()  # optional: if your dialect supports it
        )
        user = q.one()
        user.token_version = (user.token_version or 1) + 1
        # flush happens at uow boundary; return new value for convenience
        return int(user.token_version)
