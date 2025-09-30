"""Models capturing performed workouts and logged sets."""

from __future__ import annotations

from datetime import date

from sqlalchemy import UniqueConstraint

from .base import PKMixin, ReprMixin, TimestampMixin, db


class Workout(PKMixin, TimestampMixin, ReprMixin, db.Model):
    """A performed workout session recorded by a user.

    Attributes
    ----------
    user_id: sqlalchemy.Column
        Owner of the workout entry.
    routine_id: sqlalchemy.Column
        Optional routine template (:class:`app.models.routine.Routine`) the
        workout was based on.
    date: sqlalchemy.Column
        Calendar date when the workout took place.
    duration_min: sqlalchemy.Column
        Optional session duration in minutes.
    notes: sqlalchemy.Column
        Free-form notes captured after the session.
    exercises: sqlalchemy.orm.RelationshipProperty
        Ordered list of :class:`WorkoutExercise` instances logged that day.
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
    """An exercise performed within a workout session.

    Attributes
    ----------
    workout_id: sqlalchemy.Column
        Parent workout identifier with cascade deletes.
    exercise_id: sqlalchemy.Column
        Link to the catalog :class:`app.models.exercise.Exercise` performed.
    order: sqlalchemy.Column
        Display order (1-based) enforced by ``uq_workout_order``.
    notes: sqlalchemy.Column
        Optional technique or tempo notes saved during logging.
    sets: sqlalchemy.orm.RelationshipProperty
        Collection of :class:`WorkoutSet` entries for the exercise.
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
    """A single set performed for a workout exercise entry.

    Attributes
    ----------
    workout_exercise_id: sqlalchemy.Column
        Parent :class:`WorkoutExercise` identifier.
    set_index: sqlalchemy.Column
        Ordinal index enforcing uniqueness per exercise.
    reps: sqlalchemy.Column
        Count of repetitions completed for the set.
    weight_kg: sqlalchemy.Column
        Optional weight used, stored as ``Numeric(6, 2)``.
    rpe: sqlalchemy.Column
        Optional rate of perceived exertion recorded by the user.
    rir: sqlalchemy.Column
        Optional reps-in-reserve metric.
    time_sec: sqlalchemy.Column
        Optional time under tension for time-based exercises.
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
