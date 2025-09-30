"""Workout tracking models linking routines to performed sessions."""

from __future__ import annotations

from datetime import date

from sqlalchemy import UniqueConstraint

from app.core.extensions import db

from .base import PKMixin, ReprMixin, TimestampMixin


class Workout(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """Represent a completed workout session recorded by a user.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    user_id: int
        Foreign key referencing :class:`app.models.user.User`.
    routine_id: int | None
        Optional foreign key referencing the routine that inspired the session.
    date: datetime.date
        Calendar date of the workout, defaulting to ``date.today``.
    duration_min: int | None
        Optional session duration in minutes.
    notes: str | None
        Free-form notes recorded after the workout.
    user: app.models.user.User
        Relationship to the workout owner.
    routine: app.models.routine.Routine | None
        Relationship to the originating routine template, if any.
    exercises: list[WorkoutExercise]
        Ordered collection of exercises performed during the session.
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
    """Detail an exercise performed within a workout session.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    workout_id: int
        Foreign key referencing the parent :class:`Workout`.
    exercise_id: int
        Foreign key pointing to :class:`app.models.exercise.Exercise`.
    order: int
        One-based position of the exercise within the workout, enforced by a
        unique constraint per workout.
    notes: str | None
        Optional cues or tempo notes captured during execution.
    workout: Workout
        Relationship back to the parent workout.
    exercise: app.models.exercise.Exercise
        Relationship to the exercise catalog entry.
    sets: list[WorkoutSet]
        Collection of performed sets for the exercise ordered by ``set_index``.
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
    """Capture the metrics for a single set within a workout exercise.

    Attributes
    ----------
    id: int
        Surrogate primary key.
    workout_exercise_id: int
        Foreign key referencing :class:`WorkoutExercise`.
    set_index: int
        One-based ordinal enforced to be unique per workout exercise.
    reps: int
        Number of repetitions performed in the set.
    weight_kg: decimal.Decimal | None
        Optional load used for the set. ``None`` indicates bodyweight-only work.
    rpe: float | None
        Optional rate of perceived exertion.
    rir: float | None
        Optional reps in reserve value.
    time_sec: int | None
        Optional time under tension or duration value in seconds.
    workout_exercise: WorkoutExercise
        Relationship back to the parent workout exercise.
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
