"""User model storing authentication credentials and profile metadata."""

from __future__ import annotations

from typing import cast

from werkzeug.security import check_password_hash, generate_password_hash

from .base import PKMixin, ReprMixin, TimestampMixin, db


class User(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Persist local user accounts for authentication.

    Attributes
    ----------
    email: sqlalchemy.Column
        Unique email address used as the login identifier.
    name: sqlalchemy.Column
        Display name associated with the account.
    password_hash: sqlalchemy.Column
        Hashed password generated from the write-only ``password`` property.
    routines: sqlalchemy.orm.RelationshipProperty
        Collection of :class:`app.models.routine.Routine` templates owned by
        the user.
    workouts: sqlalchemy.orm.RelationshipProperty
        Collection of :class:`app.models.workout.Workout` entries logged by the
        user.

    Notes
    -----
    Password hashing relies on Werkzeug helpers and uses the application-wide
    secret configuration.
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
            Always raised because plaintext passwords are never exposed.
        """
        raise AttributeError("password is write-only")

    @password.setter
    def password(self, value: str) -> None:
        """Hash and store the password via Werkzeug utilities.

        Parameters
        ----------
        value: str
            Plaintext password provided by the caller.
        """
        self.password_hash = generate_password_hash(value)

    def verify_password(self, value: str) -> bool:
        """Check a plaintext password against the stored hash.

        Parameters
        ----------
        value: str
            Password candidate to verify.

        Returns
        -------
        bool
            ``True`` when the provided password matches the stored hash.
        """
        return cast(bool, check_password_hash(self.password_hash, value))
