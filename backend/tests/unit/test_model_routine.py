"""Unit tests for Routine planning models."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.routine import (
    RoutineDayExerciseFactory,
    RoutineDayFactory,
    RoutineExerciseSetFactory,
    RoutineFactory,
)


class TestRoutineModel:
    def test_create_basic_routine(self, session):
        r = RoutineFactory()
        session.add(r)
        session.commit()
        assert r.id is not None
        assert r.user is not None
        assert r.is_active is True

    def test_unique_routine_name_per_user(self, session):
        r1 = RoutineFactory(name="Hypertrophy")
        session.add(r1)
        session.commit()

        r2 = RoutineFactory.build(user=r1.user, name="Hypertrophy")
        session.add(r2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_day_index_uniqueness(self, session):
        d1 = RoutineDayFactory(day_index=1)
        session.add(d1)
        session.commit()

        d2 = RoutineDayFactory.build(routine=d1.routine, day_index=1)
        session.add(d2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_exercise_position_uniqueness(self, session):
        ex1 = RoutineDayExerciseFactory(position=1)
        session.add(ex1)
        session.commit()

        ex2 = RoutineDayExerciseFactory.build(routine_day=ex1.routine_day, position=1)
        session.add(ex2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_set_index_uniqueness(self, session):
        s1 = RoutineExerciseSetFactory(set_index=1)
        session.add(s1)
        session.commit()

        s2 = RoutineExerciseSetFactory.build(
            routine_day_exercise=s1.routine_day_exercise, set_index=1
        )
        session.add(s2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_relationships_navigation(self, session):
        r = RoutineFactory()
        d = RoutineDayFactory(routine=r)
        ex = RoutineDayExerciseFactory(routine_day=d)
        s = RoutineExerciseSetFactory(routine_day_exercise=ex)
        session.add_all([r, d, ex, s])
        session.commit()

        assert d in r.days
        assert ex in d.exercises
        assert s in ex.sets
        assert r.user is not None
