"""User model definition for the fitness tracking app."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy import Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.exercise_log import ExerciseSetLog
    from app.models.routine import Routine
    from app.models.workout import WorkoutSession


class User(PKMixin, ReprMixin, TimestampMixin, db.Model):
    """User entity for authentication and fitness tracking."""

    __tablename__ = "users"

    # Columns
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2))

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        Index("ix_users_created_at", "created_at"),
    )

    routines: Mapped[list[Routine]] = db.relationship(
        "Routine",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    workouts: Mapped[list[WorkoutSession]] = db.relationship(
        "WorkoutSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    exercise_logs: Mapped[list[ExerciseSetLog]] = db.relationship(
        "ExerciseSetLog",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # --- Password handling ---
    @property
    def password(self) -> str:
        raise AttributeError("password is write-only")

    @password.setter
    def password(self, value: str) -> None:
        self.password_hash = generate_password_hash(value)

    def verify_password(self, value: str) -> bool:
        return cast(bool, check_password_hash(self.password_hash, value))

    # --- Validators ---
    @validates("email")
    def _normalize_email(self, key: str, raw: str) -> str:
        value = raw.strip().lower()
        if "@" not in value:
            raise ValueError("invalid email")
        return value

    @validates("username")
    def _validate_username(self, key: str, raw: str) -> str:
        value = raw.strip()
        if not value:
            raise ValueError("username cannot be empty")
        if len(value) > 50:
            raise ValueError("username too long")
        return value

    @validates("full_name")
    def _validate_full_name(self, key: str, raw: str | None) -> str | None:
        if raw is None:
            return None
        return raw.strip() or None

    @validates("age")
    def _validate_age(self, key: str, raw: int | None) -> int | None:
        if raw is None:
            return None
        if raw < 0:
            raise ValueError("age cannot be negative")
        return raw

    @validates("height_cm")
    def _validate_height(self, key: str, raw: int | None) -> int | None:
        if raw is None:
            return None
        if raw <= 0:
            raise ValueError("height must be positive")
        return raw

    @validates("weight_kg")
    def _validate_weight(self, key: str, raw: float | None) -> float | None:
        if raw is None:
            return None
        if raw <= 0:
            raise ValueError("weight must be positive")
        return raw
