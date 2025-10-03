"""Workout session model (actual executions)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    Enum,
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
    from .cycle import Cycle
    from .routine import RoutineDay
    from .subject import Subject

# --- Domain Enum ---
WorkoutStatus = Enum("PENDING", "COMPLETED", name="workout_status")


class WorkoutSession(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """
    Workout session grouped by training day (GDPR subject pattern).

    Optionally linked to a routine day and/or a cycle to compare planned vs actual.
    """

    __tablename__ = "workout_sessions"

    # Remapped: user_id → subject_id
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    workout_date: Mapped[Any] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(WorkoutStatus, nullable=False, server_default="PENDING")

    # Optional link to routine day (must belong to same subject via routine)
    routine_day_id: Mapped[int | None] = mapped_column(
        ForeignKey("routine_days.id", ondelete="SET NULL")
    )

    # Optional link to cycle (must belong to same subject)
    cycle_id: Mapped[int | None] = mapped_column(
        ForeignKey("cycles.id", name="fk_ws_cycle_id", ondelete="SET NULL")
    )

    location: Mapped[str | None] = mapped_column(String(120))
    perceived_fatigue: Mapped[int | None] = mapped_column(Integer)
    bodyweight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("subject_id", "workout_date", name="uq_ws_subject_date"),
        Index("ix_ws_routine_day", "routine_day_id"),
        Index("ix_ws_cycle", "cycle_id"),
    )

    # Relationships
    subject: Mapped[Subject] = relationship(
        "Subject", back_populates="workouts", passive_deletes=True, lazy="selectin"
    )
    routine_day: Mapped[RoutineDay | None] = relationship(
        "RoutineDay", passive_deletes=True, lazy="selectin"
    )
    cycle: Mapped[Cycle | None] = relationship(
        "Cycle", back_populates="sessions", passive_deletes=True, lazy="selectin"
    )

    # --------- Soft validators to keep subject consistency (Python-side) ---------
    @validates("cycle_id")
    def _validate_subject_matches_cycle_by_id(self, key: str, value: int | None) -> int | None:
        """
        Ensure session.subject_id == cycle.subject_id when both present.

        This validation is best-effort and only runs when a direct ID is set and
        the referenced Cycle can be loaded.
        """
        if value is not None:
            from app.models.cycle import Cycle  # local import to avoid cycles

            cycle = db.session.get(Cycle, value)
            if cycle is not None and self.subject_id != getattr(cycle, "subject_id", None):
                raise ValueError("WorkoutSession.subject_id must match Cycle.subject_id")
        return value

    @validates("cycle")
    def _validate_subject_matches_cycle(self, key: str, cycle: Cycle | None) -> Cycle | None:
        """Ensure session.subject_id == cycle.subject_id when both present."""
        if cycle is not None and self.subject_id != getattr(cycle, "subject_id", None):
            raise ValueError("WorkoutSession.subject_id must match Cycle.subject_id")
        return cycle

    @validates("routine_day_id")
    def _validate_subject_matches_routine_by_id(self, key: str, value: int | None) -> int | None:
        """
        Ensure session.subject_id == routine.subject_id via routine_day -> routine.

        Runs on ID assignment when the RoutineDay (and its Routine) can be loaded.
        """
        if value is not None:
            from app.models.routine import RoutineDay  # local import to avoid cycles

            rd = db.session.get(RoutineDay, value)
            routine = getattr(rd, "routine", None) if rd is not None else None
            rid = getattr(routine, "subject_id", None)
            if rid is not None and self.subject_id != rid:
                raise ValueError("WorkoutSession.subject_id must match Routine.subject_id")
        return value

    @validates("routine_day")
    def _validate_subject_matches_routine(
        self, key: str, rd: RoutineDay | None
    ) -> RoutineDay | None:
        """Ensure session.subject_id == routine.subject_id when both present."""
        if rd is not None and getattr(rd, "routine", None) is not None:
            rsid = getattr(rd.routine, "subject_id", None)
            if rsid is not None and self.subject_id != rsid:
                raise ValueError("WorkoutSession.subject_id must match Routine.subject_id")
        return rd
