"""Routine execution cycles grouping workout sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .routine import Routine
    from .user import User
    from .workout import WorkoutSession


class Cycle(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Execution instance of a :class:`Routine`.

    Tracks a user's pass through a routine (cycle_number 1..N) and can be
    linked to many workout sessions for adherence/latency analytics.

    Attributes
    ----------
    user_id:
        Owner user. Duplicated from routine.user_id for fast filtering/joins.
    routine_id:
        The routine being executed in this cycle.
    cycle_number:
        Sequential number for this routine per user; starts at 1.
    started_on, ended_on:
        Optional dates to measure delays vs plan.
    notes:
        Free-form notes about the cycle.
    """

    __tablename__ = "cycles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routines.id", ondelete="CASCADE"), nullable=False
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)

    started_on: Mapped[Any | None] = mapped_column(Date)
    ended_on: Mapped[Any | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("routine_id", "cycle_number", name="uq_cycles_routine_number"),
        CheckConstraint("cycle_number > 0", name="ck_cycles_number_positive"),
        Index("ix_cycles_user_started_on", "user_id", "started_on"),
        Index("ix_cycles_routine", "routine_id"),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="cycles")
    routine: Mapped[Routine] = relationship("Routine", back_populates="cycles")
    sessions: Mapped[list[WorkoutSession]] = relationship(
        "WorkoutSession",
        back_populates="cycle",
        passive_deletes=True,
    )

    # --- Soft validator to keep user consistency (Python-side) ---
    @validates("routine_id")
    def _validate_user_matches_routine(self, key: str, rid: int) -> int:
        """Ensure cycle.user_id matches routine.user_id when loaded in-session."""
        # Only possible to check if routine already present in the identity map
        # or relationship set; otherwise skip (DB will still be consistent).
        if (
            self.user_id
            and self.routine is not None
            and self.routine.user_id
            and self.user_id != self.routine.user_id
        ):
            raise ValueError("cycle.user_id must match routine.user_id")

        return rid
