"""Catalog of exercises and enumerations for muscle groups."""

from __future__ import annotations

import enum

from .base import PKMixin, ReprMixin, TimestampMixin, db


class MuscleGroup(enum.Enum):
    """Supported muscle groups for catalogued exercises."""

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
    """Catalog entry describing a single exercise.

    Attributes
    ----------
    name: sqlalchemy.Column
        Unique exercise name used for lookup and display.
    muscle_group: sqlalchemy.Column
        Primary :class:`MuscleGroup` targeted by the exercise.
    is_unilateral: sqlalchemy.Column
        Flag indicating whether the movement trains one side at a time.
    notes: sqlalchemy.Column
        Optional free-form notes for coaching cues or equipment.
    routine_items: sqlalchemy.orm.RelationshipProperty
        Reverse relationship to :class:`app.models.routine.RoutineExercise`
        entries.
    workout_items: sqlalchemy.orm.RelationshipProperty
        Reverse relationship to :class:`app.models.workout.WorkoutExercise`
        entries.
    """

    __tablename__ = "exercises"

    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    muscle_group = db.Column(db.Enum(MuscleGroup), nullable=False, index=True)
    is_unilateral = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text)

    # Reverse relationships (no cascades from catalog)
    routine_items = db.relationship("RoutineExercise", back_populates="exercise")
    workout_items = db.relationship("WorkoutExercise", back_populates="exercise")
