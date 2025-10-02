"""Unit tests for WorkoutSession model."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.cycle import CycleFactory
from tests.factories.routine import RoutineDayFactory, RoutineFactory
from tests.factories.subject import SubjectFactory
from tests.factories.workout import WorkoutSessionFactory


class TestWorkoutSessionModel:
    def test_create_basic_session(self, session):
        ws = WorkoutSessionFactory()
        session.add(ws)
        session.commit()

        assert ws.id is not None
        assert ws.subject is not None
        assert ws.status == "PENDING"

    def test_unique_session_per_subject_per_day(self, session):
        d = datetime.date.today()

        s = SubjectFactory()
        ws1 = WorkoutSessionFactory(subject=s, workout_date=d)
        session.add(ws1)
        session.commit()

        ws2 = WorkoutSessionFactory.build(subject=s, workout_date=d)
        session.add(ws2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_optional_routine_day_link(self, session):
        ws = WorkoutSessionFactory()
        session.add(ws)
        session.commit()

        assert ws.routine_day is not None
        assert ws.routine_day.routine.subject_id == ws.subject_id

    def test_cycle_link_requires_same_subject(self, session):
        s = SubjectFactory()
        ws = WorkoutSessionFactory(subject=s)
        c = CycleFactory(subject=s)

        ws.cycle = c
        session.add_all([ws, c])
        session.commit()

        assert ws.cycle_id == c.id

    def test_cycle_link_raises_on_different_subject(self, session):
        with pytest.raises(ValueError):
            s1 = SubjectFactory()
            s2 = SubjectFactory()

            ws = WorkoutSessionFactory(subject=s1)
            c = CycleFactory(subject=s2)

            session.add_all([ws, c])
            ws.cycle = c

            session.flush()
        session.rollback()

    def test_routine_day_link_raises_on_different_subject(self, session):
        with pytest.raises(ValueError):
            s1 = SubjectFactory()
            s2 = SubjectFactory()

            routine = RoutineFactory(subject=s2)
            rd = RoutineDayFactory(routine=routine)

            ws = WorkoutSessionFactory.build(subject=s1, routine_day=rd)
            session.add(ws)

            session.flush()
        session.rollback()
