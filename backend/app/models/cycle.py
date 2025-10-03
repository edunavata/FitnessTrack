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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .routine import Routine
    from .subject import Subject
    from .workout import WorkoutSession


class Cycle(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """
    Execution instance of a :class:`Routine` by a subject.

    Notes
    -----
    - A subject can execute both owned and shared routines.
    - Cycle uniqueness is enforced per `(subject_id, routine_id, cycle_number)`.
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
        UniqueConstraint(
            "subject_id", "routine_id", "cycle_number", name="uq_cycles_subject_routine_number"
        ),
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
