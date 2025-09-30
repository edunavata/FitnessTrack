"""Exercise catalog models and enumerations."""

from __future__ import annotations

import enum

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class MuscleGroup(enum.Enum):
    """Enumerate supported primary muscle groups for cataloged exercises."""

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
    """Represent a catalog entry describing a physical exercise.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    name: str
        Unique exercise name indexed for quick lookups.
    muscle_group: MuscleGroup
        Dominant muscle group targeted by the movement.
    is_unilateral: bool
        Indicates whether the movement is performed one side at a time.
    notes: str | None
        Optional free-form instructions or cues.
    routine_items: list[RoutineExercise]
        Reverse relationship to routine prescriptions that use the exercise.
    workout_items: list[WorkoutExercise]
        Reverse relationship to performed workouts containing the exercise.
    """

    __tablename__ = "exercises"

    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    muscle_group = db.Column(db.Enum(MuscleGroup), nullable=False, index=True)
    is_unilateral = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text)

    # Reverse relationships (no cascades from catalog)
    routine_items = db.relationship("RoutineExercise", back_populates="exercise")
    workout_items = db.relationship("WorkoutExercise", back_populates="exercise")
