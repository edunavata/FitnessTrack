"""Routine planning models (mesocycles, days, exercises, sets)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .cycle import Cycle
    from .exercise import Exercise
    from .subject import Subject  # ← remapped from User to Subject


class Routine(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """
    Mesocycle template owned by a subject (GDPR subject pattern).

    Notes
    -----
    This entity is pseudonymous by design. All ownership references point to
    :class:`app.models.subject.Subject` instead of ``User``.
    """

    __tablename__ = "routines"

    # Remapped: user_id → subject_id
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        Index("ix_routines_subject_active", "subject_id", "is_active"),
        UniqueConstraint("subject_id", "name", name="uq_routines_subject_name"),
    )

    # Relationships
    subject: Mapped[Subject] = relationship(  # ← back_populates subject
        "Subject",
        back_populates="routines",
        passive_deletes=True,
        lazy="selectin",
    )
    days: Mapped[list[RoutineDay]] = relationship(
        "RoutineDay",
        back_populates="routine",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    cycles: Mapped[list[Cycle]] = relationship(
        "Cycle",
        back_populates="routine",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class RoutineDay(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Day slots within a routine cycle."""

    __tablename__ = "routine_days"

    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routines.id", ondelete="CASCADE"), nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_rest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    title: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("routine_id", "day_index", name="uq_routine_days_routine_day_index"),
    )

    # Relationships
    routine: Mapped[Routine] = relationship("Routine", back_populates="days", lazy="selectin")
    exercises: Mapped[list[RoutineDayExercise]] = relationship(
        "RoutineDayExercise",
        back_populates="routine_day",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class RoutineDayExercise(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Ordered exercises for a routine day."""

    __tablename__ = "routine_day_exercises"

    routine_day_id: Mapped[int] = mapped_column(
        ForeignKey("routine_days.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("routine_day_id", "position", name="uq_rde_day_pos"),
        Index("ix_rde_day_exercise", "routine_day_id", "exercise_id"),
    )

    # Relationships
    routine_day: Mapped[RoutineDay] = relationship(
        "RoutineDay", back_populates="exercises", lazy="selectin"
    )
    exercise: Mapped[Exercise] = relationship("Exercise", lazy="selectin")
    sets: Mapped[list[RoutineExerciseSet]] = relationship(
        "RoutineExerciseSet",
        back_populates="routine_day_exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class RoutineExerciseSet(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Planned sets per routine-day-exercise."""

    __tablename__ = "routine_exercise_sets"

    routine_day_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("routine_day_exercises.id", ondelete="CASCADE"), nullable=False
    )
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    to_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    target_weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2, asdecimal=False))
    target_reps: Mapped[int | None] = mapped_column(Integer)
    target_rir: Mapped[int | None] = mapped_column(Integer)
    target_rpe: Mapped[float | None] = mapped_column(Numeric(3, 1, asdecimal=False))
    target_tempo: Mapped[str | None] = mapped_column(String(15))
    target_rest_s: Mapped[int | None] = mapped_column(Integer)

    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("routine_day_exercise_id", "set_index", name="uq_res_rde_set_idx"),
    )

    # Relationships
    routine_day_exercise: Mapped[RoutineDayExercise] = relationship(
        "RoutineDayExercise", back_populates="sets", lazy="selectin"
    )
