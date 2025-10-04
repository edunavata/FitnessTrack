"""Unit tests for Routine planning models."""

from __future__ import annotations

import pytest

# ✅ import the ORM model, not the raw table
from app.models.routine import SubjectRoutine
from sqlalchemy.exc import IntegrityError
from tests.factories.routine import (
    RoutineDayExerciseFactory,
    RoutineDayFactory,
    RoutineExerciseSetFactory,
    RoutineFactory,
    SubjectRoutineFactory,  # ✅ use the model-based factory
)
from tests.factories.subject import SubjectFactory


class TestRoutineModel:
    def test_create_basic_routine(self, session):
        r = RoutineFactory()
        session.add(r)
        session.commit()
        assert r.id is not None
        assert r.owner is not None
        assert r.is_public is False

    def test_unique_routine_name_per_owner(self, session):
        s = SubjectFactory()
        r1 = RoutineFactory(owner=s, name="Hypertrophy")
        session.add(r1)
        session.commit()

        r2 = RoutineFactory.build(owner=s, name="Hypertrophy")
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
        assert r.owner is not None

    # --- SubjectRoutine tests (ORM model) ---
    def test_subject_can_save_routine(self, session):
        sr = SubjectRoutineFactory()
        session.commit()

        assert sr.id is not None
        assert sr.is_active is False
        assert isinstance(sr, SubjectRoutine)
        assert sr.subject_id == sr.subject.id
        assert sr.routine_id == sr.routine.id

    def test_unique_subject_routine_constraint(self, session):
        sr1 = SubjectRoutineFactory()
        session.commit()

        with pytest.raises(IntegrityError):
            # duplicate subject/routine
            SubjectRoutineFactory(subject=sr1.subject, routine=sr1.routine)
            session.commit()

    def test_subject_can_set_routine_active(self, session):
        sr = SubjectRoutineFactory()
        session.commit()

        # ✅ Update via ORM, no raw table ops
        sr.is_active = True
        session.add(sr)
        session.commit()

        # Refresh and assert
        session.refresh(sr)
        assert sr.is_active is True
