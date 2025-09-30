from __future__ import annotations

from datetime import date

from sqlalchemy import UniqueConstraint

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class Workout(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """A performed workout session (training day).

    :ivar id: Primary key.
    :ivar user_id: Owner user id.
    :ivar routine_id: Optional routine source.
    :ivar date: Calendar date.
    :ivar duration_min: Optional duration in minutes.
    :ivar notes: Free-form notes.
    """

    __tablename__ = "workouts"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    routine_id = db.Column(
        db.Integer, db.ForeignKey("routines.id", ondelete="SET NULL"), index=True
    )
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    duration_min = db.Column(db.Integer)
    notes = db.Column(db.Text)

    # Relationships
    user = db.relationship("User", back_populates="workouts")
    routine = db.relationship("Routine")
    exercises = db.relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order",
    )


class WorkoutExercise(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """An exercise performed within a workout.

    :ivar id: Primary key.
    :ivar workout_id: Parent workout id.
    :ivar exercise_id: Exercise reference.
    :ivar order: Display order (1-based).
    :ivar notes: Optional notes (tempo, cues).
    """

    __tablename__ = "workout_exercises"
    __table_args__ = (UniqueConstraint("workout_id", "order", name="uq_workout_order"),)

    workout_id = db.Column(
        db.Integer,
        db.ForeignKey("workouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False, index=True)

    order = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    # Relationships
    workout = db.relationship("Workout", back_populates="exercises")
    exercise = db.relationship("Exercise", back_populates="workout_items")
    sets = db.relationship(
        "WorkoutSet",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_index",
    )


class WorkoutSet(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """A single set performed for a workout exercise.

    :ivar id: Primary key.
    :ivar workout_exercise_id: Parent workout-exercise id.
    :ivar set_index: Ordinal set index (1-based).
    :ivar reps: Repetitions completed.
    :ivar weight_kg: Weight in kilograms (nullable for BW exercises).
    :ivar rpe: Rate of perceived exertion (nullable).
    :ivar rir: Reps in reserve (nullable).
    :ivar time_sec: Time under tension or work time in seconds (nullable, e.g., planks).
    """

    __tablename__ = "workout_sets"
    __table_args__ = (
        UniqueConstraint("workout_exercise_id", "set_index", name="uq_workout_set_index"),
    )

    workout_exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    set_index = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight_kg = db.Column(
        db.Numeric(6, 2)
    )  # allows up to 9999.99 if needed; adjust scale/precision as desired
    rpe = db.Column(db.Float)
    rir = db.Column(db.Float)
    time_sec = db.Column(db.Integer)

    # Relationships
    workout_exercise = db.relationship("WorkoutExercise", back_populates="sets")
