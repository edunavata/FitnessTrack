"""Workout routine template models."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class Routine(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Represent a reusable template of exercises planned by a user.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    user_id: int
        Foreign key referencing the owning :class:`app.models.user.User`.
    name: str
        Display name of the routine.
    notes: str | None
        Optional notes describing the intent of the routine.
    user: app.models.user.User
        ORM relationship back to the owning user.
    exercises: list[RoutineExercise]
        Ordered collection of prescribed exercises including set/rep targets.
    """

    __tablename__ = "routines"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text)

    # Relationships
    user = db.relationship("User", back_populates="routines")
    exercises = db.relationship(
        "RoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.order",
    )


class RoutineExercise(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Describe how an exercise should be performed within a routine.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    routine_id: int
        Foreign key referencing the owning :class:`Routine`.
    exercise_id: int
        Foreign key pointing to the catalog :class:`app.models.exercise.Exercise`.
    order: int
        One-based display order enforced per routine via unique constraint.
    target_sets: int
        Suggested number of sets per session.
    target_reps: int
        Suggested number of repetitions per set.
    target_rpe: float | None
        Optional target rate of perceived exertion.
    rest_sec: int
        Planned rest duration between sets in seconds.
    routine: Routine
        Relationship back to the routine template.
    exercise: app.models.exercise.Exercise
        Relationship to the exercise catalog entry.
    """

    __tablename__ = "routine_exercises"
    __table_args__ = (UniqueConstraint("routine_id", "order", name="uq_routine_order"),)

    routine_id = db.Column(
        db.Integer,
        db.ForeignKey("routines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False, index=True)

    order = db.Column(db.Integer, nullable=False)
    target_sets = db.Column(db.Integer, nullable=False, default=3)
    target_reps = db.Column(db.Integer, nullable=False, default=10)
    target_rpe = db.Column(db.Float)  # e.g., 7.5
    rest_sec = db.Column(db.Integer, nullable=False, default=120)

    # Relationships
    routine = db.relationship("Routine", back_populates="exercises")
    exercise = db.relationship("Exercise", back_populates="routine_items")
