from __future__ import annotations

from sqlalchemy import UniqueConstraint

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class Routine(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """User routine template.

    :ivar id: Primary key.
    :ivar user_id: Owner user id.
    :ivar name: Routine name.
    :ivar notes: Routine notes.
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
    """Exercise prescription inside a routine.

    :ivar id: Primary key.
    :ivar routine_id: Parent routine id.
    :ivar exercise_id: Exercise reference.
    :ivar order: Display order (1-based).
    :ivar target_sets: Planned number of sets.
    :ivar target_reps: Planned reps per set (generic).
    :ivar target_rpe: Planned RPE (nullable).
    :ivar rest_sec: Planned rest time between sets in seconds.
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
