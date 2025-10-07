"""User model definition for the fitness tracking app."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class User(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """
    Authentication identity holding direct PII only.

    The model intentionally excludes indirect PII (e.g., age, height, weight),
    which belongs to subject-scoped tables (``subject_profiles``,
    ``subject_body_metrics``) as per the GDPR subject pattern.

    Fields
    ------
    email : str
        Login email. Stored normalized (lowercase, trimmed).
    password_hash : str
        Hashed password (write-only setter via ``password``).
    username : str
        Public alias or handle. Unique per system.
    full_name : str | None
        Optional real name (direct PII).
    created_at : datetime
        Creation timestamp (from mixin).
    updated_at : datetime
        Update timestamp (from mixin).
    """

    __tablename__ = "users"

    # Columns
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(254), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Constraints & indexes
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
    )

    # -------------------- Password API --------------------
    @property
    def password(self) -> Any:  # pragma: no cover - explicit write-only contract
        """
        Disallow reading passwords.

        :raises AttributeError: Always, to ensure password is write-only.
        """
        raise AttributeError("Password is write-only.")

    @password.setter
    def password(self, raw: str) -> None:
        """
        Hash and set the password.

        :param raw: Plain text password to hash.
        :type raw: str
        """
        if not isinstance(raw, str) or not raw:
            raise ValueError("Password must be a non-empty string.")
        self.password_hash = generate_password_hash(raw)

    def verify_password(self, raw: str) -> bool:
        """
        Verify a password against the stored hash.

        :param raw: Plain text password candidate.
        :type raw: str
        :returns: ``True`` if it matches; otherwise ``False``.
        :rtype: bool
        """
        if not self.password_hash:
            return False
        # ``check_password_hash`` is not typed and returns ``Any``; coerce to bool for mypy.
        return bool(check_password_hash(self.password_hash, raw))
        # alternatively:
        # return cast(bool, check_password_hash(self.password_hash, raw))

    # -------------------- Validators --------------------
    @validates("email")
    def _normalize_email(self, key: str, value: str) -> str:
        """
        Normalize and validate email.

        :param key: Field name (``email``).
        :type key: str
        :param value: Email to normalize.
        :type value: str
        :returns: Normalized email (lowercased/trimmed).
        :rtype: str
        :raises ValueError: If email is missing or malformed.
        """
        if not value or not isinstance(value, str):
            raise ValueError("Email is required.")
        v = value.strip().lower()
        # Minimal sanity check; full validation happens at API layer.
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email format looks invalid.")
        return v

    @validates("username")
    def _normalize_username(self, key: str, value: str) -> str:
        """
        Normalize and validate username.

        :param key: Field name (``username``).
        :type key: str
        :param value: Username to normalize.
        :type value: str
        :returns: Trimmed username.
        :rtype: str
        :raises ValueError: If username is missing or only whitespace.
        """
        if not isinstance(value, str):
            raise ValueError("Username is required.")
        v = value.strip()
        if not v:
            raise ValueError("Username is required.")
        return v
