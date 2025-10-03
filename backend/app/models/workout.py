"""Workout session model (actual executions)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
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

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    workout_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(WorkoutStatus, nullable=False, server_default="PENDING")

    routine_day_id: Mapped[int | None] = mapped_column(
        ForeignKey("routine_days.id", ondelete="SET NULL")
    )
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

    subject: Mapped[Subject] = relationship(
        "Subject", back_populates="workouts", passive_deletes=True, lazy="selectin"
    )
    routine_day: Mapped[RoutineDay | None] = relationship(
        "RoutineDay", passive_deletes=True, lazy="selectin"
    )
    cycle: Mapped[Cycle | None] = relationship(
        "Cycle", back_populates="sessions", passive_deletes=True, lazy="selectin"
    )

    # --------- Validators ---------
    @validates("cycle_id")
    def _validate_subject_matches_cycle_by_id(self, key: str, value: int | None) -> int | None:
        """
        Ensure session.subject_id == cycle.subject_id when both present.
        """
        if value is not None:
            from app.models.cycle import Cycle

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

    # ❌ Se eliminan validaciones de routine_day / routine
    # Porque ahora un subject puede ejecutar una rutina que no es de su propiedad.
    # La consistencia de acceso debe controlarse en la lógica de aplicación.
