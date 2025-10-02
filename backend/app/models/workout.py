"""Workout session model (actual executions)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from marshmallow import validates
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .cycle import Cycle
    from .routine import RoutineDay
    from .user import User

# --- Domain Enum ---
WorkoutStatus = Enum("PENDING", "COMPLETED", name="workout_status")


class WorkoutSession(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Workout session grouped by training day.

    Optionally linked to a routine day for planned vs. actual tracking.
    """

    __tablename__ = "workout_sessions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workout_date: Mapped[Any] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(WorkoutStatus, nullable=False, server_default="PENDING")

    # Optional link to routine day
    routine_day_id: Mapped[int | None] = mapped_column(
        ForeignKey("routine_days.id", ondelete="SET NULL")
    )

    cycle_id: Mapped[int | None] = mapped_column(
        ForeignKey("cycles.id", name="fk_ws_cycle_id", ondelete="SET NULL")
    )

    location: Mapped[str | None] = mapped_column(String(120))
    perceived_fatigue: Mapped[int | None] = mapped_column(Integer)
    bodyweight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("user_id", "workout_date", name="uq_ws_user_date"),
        Index("ix_ws_routine_day", "routine_day_id"),
        Index("ix_ws_cycle", "cycle_id"),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="workouts")
    routine_day: Mapped[RoutineDay | None] = relationship("RoutineDay")
    cycle: Mapped[Cycle | None] = relationship("Cycle", back_populates="sessions")

    # inside WorkoutSession
    @validates("cycle_id")
    def _validate_cycle_user(self, key: str, value: int | None) -> int | None:
        """Ensure the cycle belongs to the same user as the workout session."""
        if value is not None:
            from app.models.cycle import Cycle

            cycle = db.session.get(Cycle, value)
            if cycle and cycle.user_id != self.user_id:
                raise ValueError("WorkoutSession.user_id must match Cycle.user_id")
        return value

    @validates("cycle")
    def _validate_cycle(self, key, cycle):
        if cycle is not None and cycle.user_id != self.user_id:
            raise ValueError("WorkoutSession.user_id must match Cycle.user_id")
        return cycle
