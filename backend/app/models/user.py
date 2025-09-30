"""User model definition."""

from __future__ import annotations

from typing import cast

from werkzeug.security import check_password_hash, generate_password_hash

from .base import PKMixin, ReprMixin, TimestampMixin, db


class User(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Minimal user entity (later extended for JWT auth).

    Attributes
    ----------
    id:
        Primary key.
    email:
        Unique email address.
    password_hash:
        Hashed user password.
    created_at:
        Creation timestamp.
    """

    __tablename__ = "users"

    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationships
    routines = db.relationship("Routine", back_populates="user", cascade="all, delete-orphan")
    workouts = db.relationship("Workout", back_populates="user", cascade="all, delete-orphan")

    @property
    def password(self) -> str:
        """Prevent reading the raw password."""
        raise AttributeError("password is write-only")

    @password.setter
    def password(self, value: str) -> None:
        """Hash and store the password."""
        self.password_hash = generate_password_hash(value)

    def verify_password(self, value: str) -> bool:
        """Check a plaintext password against the stored hash."""
        return cast(bool, check_password_hash(self.password_hash, value))
