"""User model definition supporting password hashing for JWT auth."""

from __future__ import annotations

from typing import cast

from werkzeug.security import check_password_hash, generate_password_hash

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class User(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Minimal user entity used for authentication and ownership.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    email: str
        Unique login identifier validated at the database level.
    name: str
        Display name stored alongside the email address.
    password_hash: str
        Hash computed by :func:`werkzeug.security.generate_password_hash`.
    created_at: datetime.datetime
        Timestamp set when the record is inserted.
    updated_at: datetime.datetime
        Timestamp refreshed whenever the record mutates.
    routines: list[app.models.routine.Routine]
        Collection of routine templates owned by the user.
    workouts: list[app.models.workout.Workout]
        Collection of recorded workouts associated with the user.
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
        """Prevent reading the raw password.

        Raises
        ------
        AttributeError
            Always raised to prevent disclosure of secret credentials.

        Notes
        -----
        The property is intentionally write-only; use :meth:`verify_password`
        to check credentials instead of reading them back.
        """
        raise AttributeError("password is write-only")

    @password.setter
    def password(self, value: str) -> None:
        """Hash and store the password.

        Parameters
        ----------
        value: str
            Plaintext password which will be transformed using
            :func:`werkzeug.security.generate_password_hash`.
        """
        self.password_hash = generate_password_hash(value)

    def verify_password(self, value: str) -> bool:
        """Check a plaintext password against the stored hash.

        Parameters
        ----------
        value: str
            Password candidate provided by a client.

        Returns
        -------
        bool
            ``True`` when the candidate matches ``password_hash``;
            ``False`` otherwise.
        """
        return cast(bool, check_password_hash(self.password_hash, value))
