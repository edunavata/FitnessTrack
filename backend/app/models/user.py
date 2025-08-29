"""User model definition."""

from __future__ import annotations

from typing import cast

from werkzeug.security import check_password_hash, generate_password_hash

from app.core.database import db


class User(db.Model):
    """Minimal user entity (we ampliaremos luego para auth JWT).

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

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

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
