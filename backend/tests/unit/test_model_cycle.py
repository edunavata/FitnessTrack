"""Unit tests for Cycle model."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.cycle import CycleFactory
from tests.factories.routine import RoutineFactory
from tests.factories.user import UserFactory
from tests.factories.workout import WorkoutSessionFactory


class TestCycleModel:
    def test_create_basic_cycle(self, session):
        c = CycleFactory()
        session.add(c)
        session.commit()

        assert c.id is not None
        assert c.user is not None
        assert c.routine is not None
        assert c.cycle_number == 1

    def test_unique_cycle_number_per_routine(self, session):
        c1 = CycleFactory(cycle_number=1)
        session.add(c1)
        session.commit()

        c2 = CycleFactory.build(routine=c1.routine, user=c1.user, cycle_number=1)
        session.add(c2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_same_cycle_number_allowed_on_other_routine(self, session):
        user = UserFactory()
        r1 = RoutineFactory(user=user, name="R1")
        r2 = RoutineFactory(user=user, name="R2")
        c1 = CycleFactory(routine=r1, user=user, cycle_number=1)
        c2 = CycleFactory(routine=r2, user=user, cycle_number=1)

        session.add_all([c1, c2])
        session.commit()

        assert c1.id != c2.id

    def test_workout_session_can_link_to_cycle_if_same_user(self, session):
        c = CycleFactory()
        ws = WorkoutSessionFactory(user=c.user)  # same user
        ws.cycle = c

        session.add_all([c, ws])
        session.commit()

        assert ws.cycle_id == c.id
        assert ws in c.sessions
