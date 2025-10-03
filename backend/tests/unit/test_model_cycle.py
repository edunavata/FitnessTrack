"""Unit tests for Cycle model."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.cycle import CycleFactory
from tests.factories.routine import RoutineFactory
from tests.factories.subject import SubjectFactory
from tests.factories.workout import WorkoutSessionFactory


class TestCycleModel:
    def test_create_basic_cycle(self, session):
        c = CycleFactory()
        session.add(c)
        session.commit()

        assert c.id is not None
        assert c.subject is not None
        assert c.routine is not None
        assert c.cycle_number == 1

    def test_unique_cycle_number_per_subject_and_routine(self, session):
        c1 = CycleFactory(cycle_number=1)
        session.add(c1)
        session.commit()

        # mismo subject y misma rutina → debe violar constraint
        c2 = CycleFactory.build(routine=c1.routine, subject=c1.subject, cycle_number=1)
        session.add(c2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_same_cycle_number_allowed_for_other_routine(self, session):
        s = SubjectFactory()
        r1 = RoutineFactory(owner=s, name="R1")
        r2 = RoutineFactory(owner=s, name="R2")
        c1 = CycleFactory(routine=r1, subject=s, cycle_number=1)
        c2 = CycleFactory(routine=r2, subject=s, cycle_number=1)

        session.add_all([c1, c2])
        session.commit()

        assert c1.id != c2.id
        assert c1.subject_id == c2.subject_id  # same subject across routines

    def test_same_cycle_number_allowed_for_other_subject(self, session):
        r = RoutineFactory()  # rutina de un owner cualquiera
        s1 = SubjectFactory()
        s2 = SubjectFactory()

        c1 = CycleFactory(routine=r, subject=s1, cycle_number=1)
        c2 = CycleFactory(routine=r, subject=s2, cycle_number=1)

        session.add_all([c1, c2])
        session.commit()

        assert c1.id != c2.id
        assert c1.routine_id == c2.routine_id
        assert c1.subject_id != c2.subject_id

    def test_workout_session_can_link_to_cycle_if_same_subject(self, session):
        c = CycleFactory()
        ws = WorkoutSessionFactory(subject=c.subject)  # same subject
        ws.cycle = c

        session.add_all([c, ws])
        session.commit()

        assert ws.cycle_id == c.id
        assert ws in c.sessions
