"""Models for training routines and their prescribed exercises."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from .base import PKMixin, ReprMixin, TimestampMixin, db


class Routine(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Template describing a user's planned workout routine.

    Attributes
    ----------
    user_id: sqlalchemy.Column
        Foreign key referencing :class:`app.models.user.User` who owns the
        routine.
    name: sqlalchemy.Column
        Human-readable routine name shown to the user.
    notes: sqlalchemy.Column
        Optional free-form notes explaining the routine intent.
    exercises: sqlalchemy.orm.RelationshipProperty
        Ordered collection of :class:`RoutineExercise` prescriptions.
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
    """Exercise prescription belonging to a routine template.

    Attributes
    ----------
    routine_id: sqlalchemy.Column
        Parent routine identifier with cascade deletes.
    exercise_id: sqlalchemy.Column
        Reference to the catalog :class:`app.models.exercise.Exercise`.
    order: sqlalchemy.Column
        Display order (1-based) enforced by ``uq_routine_order``.
    target_sets: sqlalchemy.Column
        Planned number of sets for the exercise.
    target_reps: sqlalchemy.Column
        Planned repetitions per set.
    target_rpe: sqlalchemy.Column
        Optional target rate of perceived exertion.
    rest_sec: sqlalchemy.Column
        Rest time between sets in seconds.
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
