"""Secondary muscle mapping for exercises."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db

from .base import ReprMixin

if TYPE_CHECKING:
    from .exercise import Exercise


class ExerciseSecondaryMuscle(ReprMixin, db.Model):
    """Normalized mapping for secondary muscles of an exercise."""

    __tablename__ = "exercise_secondary_muscles"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    muscle: Mapped[str] = mapped_column(String(50), primary_key=True)

    __table_args__ = (
        UniqueConstraint("exercise_id", "muscle", name="uq_exercise_muscle"),
        Index("ix_exercise_muscle", "exercise_id", "muscle"),
    )

    # Relationships
    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="secondary_muscles")
