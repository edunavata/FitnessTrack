"""Authentication domain services."""

from __future__ import annotations

from typing import Mapping

from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict, Unauthorized
from app.repositories import UserRepository

from . import get_session


class AuthService:
    """Coordinate registration and authentication operations."""

    def __init__(self, session=None) -> None:
        self.session = get_session(session)
        self.users = UserRepository()

    def register_user(self, data: Mapping[str, object]):
        """Register a new user and return the persisted entity."""

        try:
            user = self.users.create(self.session, data)
            # TODO: Integrate password hashing/pepper strategy before persistence.
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover - depends on DB backend
            self.session.rollback()
            raise Conflict("User already exists") from exc
        return user

    def authenticate(self, email: str, password: str):
        """Validate credentials and return the matching user."""

        user = self.users.get_by_email(self.session, email)
        if user is None or not user.verify_password(password):
            raise Unauthorized("Invalid credentials")
        return user

    def issue_access_token(self, user) -> str:
        """Issue a short-lived JWT access token for the given user."""

        identity = str(user.id)
        # TODO: Add refresh tokens, roles, and fine-grained scope claims.
        return create_access_token(identity=identity, additional_claims={"scopes": ["user:read"]})

    def login(self, email: str, password: str) -> tuple[str, object]:
        """Authenticate credentials and return ``(token, user)``."""

        user = self.authenticate(email, password)
        token = self.issue_access_token(user)
        return token, user

    def whoami(self, identity: str | int):
        """Return the user referenced by the JWT identity."""

        try:
            user_id = int(identity)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            raise Unauthorized("Invalid token subject") from None
        user = self.users.get_by_id(self.session, user_id)
        if user is None:
            raise Unauthorized("User not found")
        return user
