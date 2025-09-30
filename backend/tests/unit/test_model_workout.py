"""Unit tests for Workout, WorkoutExercise, and WorkoutSet models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import NoneType

import pytest
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import RoutineFactory
from tests.factories.workout import (
    WorkoutExerciseFactory,
    WorkoutFactory,
    WorkoutSetFactory,
)


class TestWorkoutModel:
    """Tests for the Workout entity."""

    @pytest.mark.unit
    def test_create_basic_workout(self, session):
        """Validate workout creation defaults.

        Arrange a workout from the factory tied to a user.
        Act by flushing the session.
        Assert ownership, date, and timestamps populate.
        """
        w = WorkoutFactory()
        session.add(w)
        session.flush()

        assert w.id is not None
        assert w.user is not None
        assert isinstance(w.date, date)
        assert w.created_at is not None and w.updated_at is not None

    @pytest.mark.unit
    def test_user_required(self, session):
        """Arrange a workout without ``user_id``, flush, and expect an integrity failure."""
        session.add(Workout(user_id=None))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_optional_routine_and_duration(self, session):
        """Arrange a workout with optional fields, flush, and confirm nullable columns persist."""
        r = RoutineFactory()
        w = WorkoutFactory(duration_min=45)
        # Optionally associate a specific routine for this scenario.
        w.routine = r

        session.add_all([r, w])
        session.flush()

        assert w.routine_id == r.id
        assert w.duration_min == 45


class TestWorkoutExerciseModel:
    """Tests for the WorkoutExercise entity."""

    @pytest.mark.unit
    def test_create_basic_workout_exercise(self, session):
        """Validate workout exercise creation.

        Arrange with the factory to include workout and exercise relations.
        Act by flushing the session.
        Assert relationship links and timestamps populate.
        """
        we = WorkoutExerciseFactory()
        session.add(we)
        session.flush()

        assert we.id is not None
        assert we.workout is not None and we.exercise is not None
        assert we.order >= 1
        assert we.created_at is not None and we.updated_at is not None

    @pytest.mark.unit
    def test_order_unique_within_workout(self, session):
        """Reject duplicate workout exercise ordering.

        Arrange two exercises with the same ``order`` on one workout.
        Act by flushing both records.
        Assert the unique constraint raises an integrity error.
        """
        w = WorkoutFactory()
        ex1 = ExerciseFactory(name="Bench Press")
        ex2 = ExerciseFactory(name="Incline Bench")
        session.add_all([w, ex1, ex2])
        session.flush()

        a = WorkoutExercise(workout_id=w.id, exercise_id=ex1.id, order=1)
        b = WorkoutExercise(
            workout_id=w.id, exercise_id=ex2.id, order=1
        )  # same order, same workout
        session.add_all([a, b])

        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_same_order_allowed_in_different_workouts(self, session):
        """Permit matching orders across workouts.

        Arrange exercises mapped to different workouts with order ``1``.
        Act by flushing both inserts.
        Assert no integrity error occurs.
        """
        w1 = WorkoutFactory()
        w2 = WorkoutFactory()
        ex = ExerciseFactory(name="Row")
        session.add_all([w1, w2, ex])
        session.flush()

        a = WorkoutExercise(workout_id=w1.id, exercise_id=ex.id, order=1)
        b = WorkoutExercise(workout_id=w2.id, exercise_id=ex.id, order=1)
        session.add_all([a, b])
        session.flush()  # should not raise

    @pytest.mark.unit
    def test_relationship_ordering_by_order(self, session):
        """Order workout exercises by column value.

        Arrange inserts out of order.
        Act by accessing ``workout.exercises``.
        Assert the relationship sorts by the ``order`` column.
        """
        w = WorkoutFactory()
        ex1 = ExerciseFactory(name="Lat Pulldown")
        ex2 = ExerciseFactory(name="Seated Row")
        ex3 = ExerciseFactory(name="Face Pull")
        session.add_all([w, ex1, ex2, ex3])
        session.flush()

        # Create out of order on purpose
        e2 = WorkoutExercise(workout_id=w.id, exercise_id=ex2.id, order=2)
        e3 = WorkoutExercise(workout_id=w.id, exercise_id=ex3.id, order=3)
        e1 = WorkoutExercise(workout_id=w.id, exercise_id=ex1.id, order=1)
        session.add_all([e2, e3, e1])
        session.flush()

        orders = [item.order for item in w.exercises]
        assert orders == [1, 2, 3]

    @pytest.mark.unit
    def test_delete_workout_cascades_children(self, session):
        """Cascade workout deletions to dependents.

        Arrange a workout with generated nested children.
        Act by deleting the workout parent.
        Assert cascades remove exercises and sets.
        """
        ws = WorkoutSetFactory()  # creates workout, workout_exercise, and set
        w = ws.workout_exercise.workout
        we = ws.workout_exercise
        session.add(ws)
        session.flush()

        w_id, we_id, ws_id = w.id, we.id, ws.id

        # Delete the parent workout
        session.delete(w)
        session.flush()

        assert session.get(Workout, w_id) is None
        assert session.get(WorkoutExercise, we_id) is None
        assert session.get(WorkoutSet, ws_id) is None


class TestWorkoutSetModel:
    """Tests for the WorkoutSet entity."""

    @pytest.mark.unit
    def test_create_basic_set(self, session):
        """Validate workout set creation.

        Arrange a set from the factory tied to a workout exercise.
        Act by flushing the session.
        Assert defaults, relationships, and timestamps remain intact.
        """
        s = WorkoutSetFactory()
        session.add(s)
        session.flush()

        assert s.id is not None
        assert s.workout_exercise is not None
        assert s.set_index >= 1
        assert s.reps == 10
        # weight_kg stored as Decimal (dialect dependent, but SQLAlchemy returns Decimal normally)
        assert isinstance(s.weight_kg, Decimal | NoneType)
        assert s.created_at is not None and s.updated_at is not None

    @pytest.mark.unit
    def test_set_index_unique_within_workout_exercise(self, session):
        """Reject duplicate set indexes within an exercise.

        Arrange two sets on the same workout exercise sharing ``set_index``.
        Act by flushing both rows.
        Assert the uniqueness constraint raises an error.
        """
        we = WorkoutExerciseFactory()
        session.add(we)
        session.flush()

        a = WorkoutSet(workout_exercise_id=we.id, set_index=1, reps=8)
        b = WorkoutSet(workout_exercise_id=we.id, set_index=1, reps=10)  # duplicate index
        session.add_all([a, b])

        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_nullable_metrics_fields(self, session):
        """Preserve optional workout set metrics.

        Arrange a set with all nullable metrics set to ``None``.
        Act by flushing and reloading the row.
        Assert retrieval keeps each metric at ``None``.
        """
        we = WorkoutExerciseFactory()
        s = WorkoutSet(
            workout_exercise_id=we.id,
            set_index=1,
            reps=12,
            weight_kg=None,
            rpe=None,
            rir=None,
            time_sec=None,
        )
        session.add_all([we, s])
        session.flush()

        got = session.get(WorkoutSet, s.id)
        assert got is not None
        assert got.weight_kg is None
        assert got.rpe is None
        assert got.rir is None
        assert got.time_sec is None
