"""Authentication domain services."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.repositories import UserRepository

from . import get_session


class AuthService:
    """Coordinate registration and authentication operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.users = UserRepository()

    def register_user(self, data: Mapping[str, object]):
        """Register a new user returning a placeholder entity.

        The implementation intentionally avoids database access to keep the
        skeleton lightweight. A future revision should hash passwords,
        validate uniqueness, and persist through :class:`UserRepository`.
        """

        # TODO: Hash passwords and persist through the repository once wiring exists.
        return self.users.create(self.session, data)

    def login(self, email: str, password: str) -> tuple[str, SimpleNamespace]:
        """Return a mock access token and user profile.

        Parameters
        ----------
        email:
            User's email address.
        password:
            Raw password used only for future validation hooks.
        """

        # TODO: Validate credentials against persisted users.
        token = uuid4().hex
        now = datetime.now(UTC)
        user = SimpleNamespace(
            id=0,
            email=email,
            username=email.split("@")[0],
            full_name=None,
            created_at=now,
            updated_at=now,
        )
        return token, user

    def whoami(self, identity: str | int) -> SimpleNamespace:
        """Return a lightweight profile for the provided identity.

        TODO
        ----
        Replace this stub with a repository lookup and proper error handling.
        """

        try:
            numeric_id = int(identity)
        except (TypeError, ValueError):
            numeric_id = 0
        email = f"user{numeric_id}@example.com"
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=numeric_id,
            email=email,
            username=email.split("@")[0],
            full_name=None,
            created_at=now,
            updated_at=now,
        )
