"""Exercise set logs (actual performed sets)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

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
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .exercise import Exercise
    from .routine import RoutineExerciseSet
    from .subject import Subject
    from .workout import WorkoutSession


class ExerciseSetLog(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """
    Per-set execution log (actuals), optionally linked to a planned set.

    GDPR subject pattern
    --------------------
    Ownership is by ``subject_id`` (pseudonymous). Optional links to
    :class:`WorkoutSession` and :class:`RoutineExerciseSet` must refer to the
    *same* subject. Validation is performed via FK id-based validators so that
    errors surface on ``flush``/``commit`` (not at attribute assignment time),
    matching test expectations.
    """

    __tablename__ = "exercise_set_logs"

    # --- Who and what (remapped user -> subject) ---
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
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
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
        Index("ix_esl_subject_time", "subject_id", "performed_at"),
        Index("ix_esl_exercise_time", "exercise_id", "performed_at"),
        UniqueConstraint(
            "subject_id",
            "exercise_id",
            "performed_at",
            "set_index",
            name="uq_esl_session_set",
        ),
        Index("ix_esl_by_session", "subject_id", "exercise_id", "session_id", "set_index"),
        Index("ix_esl_planned", "planned_set_id"),
    )

    # --- Relationships ---
    subject: Mapped[Subject] = relationship(
        "Subject", back_populates="exercise_logs", passive_deletes=True, lazy="selectin"
    )
    exercise: Mapped[Exercise] = relationship("Exercise", passive_deletes=True, lazy="selectin")
    session: Mapped[WorkoutSession | None] = relationship(
        "WorkoutSession", passive_deletes=True, lazy="selectin"
    )
    planned_set: Mapped[RoutineExerciseSet | None] = relationship(
        "RoutineExerciseSet", passive_deletes=True, lazy="selectin"
    )

    # ---------------- Validation (id-based; triggers on flush/commit) ----------------
    @validates("session_id")
    def _validate_subject_matches_session_id(self, key: str, value: int | None) -> int | None:
        """
        Ensure ``subject_id`` equals the related ``WorkoutSession.subject_id``.

        This validator runs when ``session_id`` changes; SQLAlchemy resolves the FK
        before/at flush time so mismatches raise on ``flush``/``commit``, not at
        attribute assignment.

        :param key: Field name (``"session_id"``).
        :param value: The candidate session primary key.
        :returns: The same value if valid.
        :raises ValueError: If subjects differ.
        """
        if value is None:
            return value
        from app.models.workout import WorkoutSession

        sess = db.session.get(WorkoutSession, value)
        if sess is None:
            return value  # Let FK/DB constraints handle non-existent rows.

        sess_sid = getattr(sess, "subject_id", None)
        if self.subject_id is not None and sess_sid is not None and self.subject_id != sess_sid:
            raise ValueError("ExerciseSetLog.subject_id must match WorkoutSession.subject_id")
        return value

    @validates("planned_set_id")
    def _validate_subject_matches_planned_id(self, key: str, value: int | None) -> int | None:
        """
        Ensure ``subject_id`` equals the owning ``Routine.subject_id`` of the planned set.

        :param key: Field name (``"planned_set_id"``).
        :param value: The candidate planned set primary key.
        :returns: The same value if valid.
        :raises ValueError: If subjects differ.
        """
        if value is None:
            return value
        from app.models.routine import RoutineExerciseSet

        pes = db.session.get(RoutineExerciseSet, value)
        if pes is None:
            return value  # Let FK/DB constraints handle missing rows.

        # Walk: PES -> RoutineDayExercise -> RoutineDay -> Routine -> subject_id
        routine = getattr(
            getattr(getattr(pes, "routine_day_exercise", None), "routine_day", None),
            "routine",
            None,
        )
        routine_subject_id = getattr(routine, "subject_id", None)

        if (
            self.subject_id is not None
            and routine_subject_id is not None
            and self.subject_id != routine_subject_id
        ):
            raise ValueError("ExerciseSetLog.subject_id must match Routine.subject_id")
        return value

    # NOTE:
    # We intentionally avoid relationship-level validators for `session` and
    # `planned_set` because they fire on attribute assignment and would raise
    # too early for the tests, which expect validation at `flush` time.
