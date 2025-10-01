"""Exercise set logs (actual performed sets)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
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
    from .exercise import Exercise
    from .routine import RoutineExerciseSet
    from .user import User
    from .workout import WorkoutSession


class ExerciseSetLog(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Per-set execution log (actuals), optionally linked to planned set."""

    __tablename__ = "exercise_set_logs"

    # --- Who and what ---
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="SET NULL")
    )
    planned_set_id: Mapped[int | None] = mapped_column(
        ForeignKey("routine_exercise_sets.id", ondelete="SET NULL")
    )

    # --- Timing & ordering ---
    performed_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    to_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # --- Actuals (performed) ---
    actual_weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    actual_reps: Mapped[int | None] = mapped_column(Integer)
    actual_rir: Mapped[int | None] = mapped_column(Integer)
    actual_rpe: Mapped[float | None] = mapped_column(Numeric(3, 1))
    actual_tempo: Mapped[str | None] = mapped_column(String(15))
    actual_rest_s: Mapped[int | None] = mapped_column(Integer)

    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_esl_user_time", "user_id", "performed_at"),
        Index("ix_esl_exercise_time", "exercise_id", "performed_at"),
        UniqueConstraint(
            "user_id",
            "exercise_id",
            "performed_at",
            "set_index",
            name="uq_esl_session_set",
        ),
        Index("ix_esl_by_session", "user_id", "exercise_id", "session_id", "set_index"),
        Index("ix_esl_planned", "planned_set_id"),
    )

    # --- Relationships ---
    user: Mapped[User] = relationship("User", back_populates="exercise_logs")
    exercise: Mapped[Exercise] = relationship("Exercise")
    session: Mapped[WorkoutSession | None] = relationship("WorkoutSession")
    planned_set: Mapped[RoutineExerciseSet | None] = relationship("RoutineExerciseSet")
