from __future__ import annotations

import enum

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class MuscleGroup(enum.Enum):
    """Supported muscle groups."""

    CHEST = "CHEST"
    BACK = "BACK"
    SHOULDERS = "SHOULDERS"
    QUADS = "QUADS"
    HAMSTRINGS = "HAMSTRINGS"
    GLUTES = "GLUTES"
    BICEPS = "BICEPS"
    TRICEPS = "TRICEPS"
    CALVES = "CALVES"
    ABS = "ABS"
    FULL_BODY = "FULL_BODY"
    OTHER = "OTHER"


class Exercise(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Exercise catalog entity.

    :ivar id: Primary key.
    :ivar name: Unique exercise name.
    :ivar muscle_group: Main muscle group (enum).
    :ivar is_unilateral: Whether exercise is unilateral.
    :ivar notes: Free-form notes.
    """

    __tablename__ = "exercises"

    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    muscle_group = db.Column(db.Enum(MuscleGroup), nullable=False, index=True)
    is_unilateral = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text)

    # Reverse relationships (no cascades from catalog)
    routine_items = db.relationship("RoutineExercise", back_populates="exercise")
    workout_items = db.relationship("WorkoutExercise", back_populates="exercise")
