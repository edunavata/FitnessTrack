"""Unit tests validating Routine and RoutineExercise persistence rules."""

from __future__ import annotations

import pytest
from app.models.routine import Routine, RoutineExercise
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import RoutineExerciseFactory, RoutineFactory
from tests.factories.user import UserFactory


class TestRoutineModel:
    """Tests for the Routine entity."""

    @pytest.mark.unit
    def test_create_basic_routine(self, session):
        """Validate basic routine persistence.

        Arrange with a factory routine linked to a user.
        Act by flushing the session.
        Assert ownership and timestamps populate.
        """
        r = RoutineFactory()
        session.add(r)
        session.flush()

        assert r.id is not None
        assert r.user is not None
        assert r.created_at is not None
        assert r.updated_at is not None

    @pytest.mark.unit
    def test_name_required(self, session):
        """Reject nameless routines.

        Arrange a routine factory override without ``name``.
        Act by flushing the session.
        Assert the database raises an integrity error.
        """
        u = UserFactory()
        session.add(u)
        session.flush()

        session.add(Routine(user_id=u.id, name=None))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_user_required(self, session):
        """Enforce routine ownership.

        Arrange a routine missing ``user_id``.
        Act by flushing the session.
        Assert integrity enforcement triggers.
        """
        session.add(Routine(user_id=None, name="No owner"))
        with pytest.raises(IntegrityError):
            session.flush()


class TestRoutineExerciseModel:
    """Tests for the RoutineExercise entity."""

    @pytest.mark.unit
    def test_create_basic_routine_exercise(self, session):
        """Validate routine exercise defaults.

        Arrange with the factory and its linked routine and exercise.
        Act by flushing the session.
        Assert defaults, relationships, and timestamps populate.
        """
        rx = RoutineExerciseFactory()
        session.add(rx)
        session.flush()

        assert rx.id is not None
        assert rx.routine is not None and rx.exercise is not None
        assert rx.order >= 1
        # defaults
        assert rx.target_sets == 3
        assert rx.target_reps == 10
        assert rx.rest_sec == 120
        # nullable field can be None by default
        assert rx.target_rpe is None
        # timestamps
        assert rx.created_at is not None
        assert rx.updated_at is not None

    @pytest.mark.unit
    def test_order_unique_within_routine(self, session):
        """Prevent duplicate routine exercise ordering.

        Arrange two exercises sharing an order on one routine.
        Act by flushing both to the database.
        Assert the unique constraint raises an integrity error.
        """
        r = RoutineFactory()
        e1 = ExerciseFactory(name="Bench Press")
        e2 = ExerciseFactory(name="Incline Bench")

        session.add_all([r, e1, e2])
        session.flush()

        a = RoutineExercise(routine_id=r.id, exercise_id=e1.id, order=1)
        b = RoutineExercise(routine_id=r.id, exercise_id=e2.id, order=1)  # same order, same routine

        session.add_all([a, b])
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_same_order_allowed_in_different_routines(self, session):
        """Allow shared orders across routines.

        Arrange exercises in separate routines with the same order.
        Act by flushing both to the session.
        Assert the constraint allows the inserts.
        """
        r1 = RoutineFactory(name="A")
        r2 = RoutineFactory(name="B")
        ex = ExerciseFactory(name="Row")

        session.add_all([r1, r2, ex])
        session.flush()

        a = RoutineExercise(routine_id=r1.id, exercise_id=ex.id, order=1)
        b = RoutineExercise(routine_id=r2.id, exercise_id=ex.id, order=1)

        session.add_all([a, b])
        session.flush()  # should not raise

    @pytest.mark.unit
    def test_relationship_ordering_by_order(self, session):
        """Ensure relationship ordering uses the column.

        Arrange routine exercises inserted out of order.
        Act by loading ``routine.exercises``.
        Assert the sequence follows the ``order`` column.
        """
        r = RoutineFactory()
        e1 = ExerciseFactory(name="Lat Pulldown")
        e2 = ExerciseFactory(name="Seated Row")
        e3 = ExerciseFactory(name="Face Pull")

        session.add_all([r, e1, e2, e3])
        session.flush()

        # Create out of order on purpose
        rx2 = RoutineExercise(routine_id=r.id, exercise_id=e2.id, order=2)
        rx3 = RoutineExercise(routine_id=r.id, exercise_id=e3.id, order=3)
        rx1 = RoutineExercise(routine_id=r.id, exercise_id=e1.id, order=1)
        session.add_all([rx2, rx3, rx1])
        session.flush()

        # Access relationship; should come sorted by `order`
        orders = [item.order for item in r.exercises]
        assert orders == [1, 2, 3]

    @pytest.mark.unit
    def test_delete_routine_cascades_children_via_orphan(self, session):
        """Cascade routine deletions to children.

        Arrange a routine with a dependent routine exercise.
        Act by deleting the parent routine.
        Assert delete-orphan cascading removes the child row.
        """
        rx = RoutineExerciseFactory()
        session.add(rx)
        session.flush()

        rid = rx.routine_id
        rx_id = rx.id

        # Delete the parent routine
        session.delete(rx.routine)
        session.flush()

        # Child should be gone due to relationship cascade="all, delete-orphan"
        assert session.get(Routine, rid) is None
        assert session.get(RoutineExercise, rx_id) is None
