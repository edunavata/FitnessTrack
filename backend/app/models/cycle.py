"""Routine execution cycles grouping workout sessions."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

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
    from .subject import Subject
    from .workout import WorkoutSession


class Cycle(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """
    Execution instance of a :class:`Routine`.

    Tracks a subject's pass through a routine (cycle_number 1..N) and can be
    linked to many workout sessions for adherence/latency analytics.

    Attributes
    ----------
    subject_id:
        Owner subject. Duplicated from routine.subject_id for fast filtering/joins.
    routine_id:
        The routine being executed in this cycle.
    cycle_number:
        Sequential number for this routine per subject; starts at 1.
    started_on, ended_on:
        Optional dates to measure delays vs plan.
    notes:
        Free-form notes about the cycle.
    """

    __tablename__ = "cycles"

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routines.id", ondelete="CASCADE"), nullable=False
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)

    started_on: Mapped[date | None] = mapped_column(Date)
    ended_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("routine_id", "cycle_number", name="uq_cycles_routine_number"),
        CheckConstraint("cycle_number > 0", name="ck_cycles_number_positive"),
        Index("ix_cycles_subject_started_on", "subject_id", "started_on"),
        Index("ix_cycles_routine", "routine_id"),
    )

    # Relationships
    subject: Mapped[Subject] = relationship(
        "Subject", back_populates="cycles", passive_deletes=True, lazy="selectin"
    )
    routine: Mapped[Routine] = relationship(
        "Routine", back_populates="cycles", passive_deletes=True, lazy="selectin"
    )
    sessions: Mapped[list[WorkoutSession]] = relationship(
        "WorkoutSession",
        back_populates="cycle",
        passive_deletes=True,
        lazy="selectin",
    )

    # --- Soft validator to keep subject consistency (Python-side) ---
    @validates("routine_id")
    def _validate_subject_matches_routine(self, key: str, rid: int | None) -> int | None:
        """
        Ensure cycle.subject_id equals routine.subject_id when both are present.

        Validation is performed using the FK id so it triggers on flush/commit time,
        not at relationship attribute assignment.
        """
        if rid is None:
            return rid

        from app.models.routine import Routine  # local import to avoid cycles

        routine = db.session.get(Routine, rid)
        if (
            routine is not None
            and getattr(routine, "subject_id", None) is not None
            and getattr(self, "subject_id", None) is not None
            and self.subject_id != routine.subject_id
        ):
            raise ValueError("cycle.subject_id must match routine.subject_id")
        return rid

    # OPTIONAL: if you currently have a relationship-level validator like:
    # @validates("routine") ... -> remove it to avoid eager raises.
