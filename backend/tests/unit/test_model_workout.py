"""Unit tests for WorkoutSession model."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.workout import WorkoutSessionFactory


class TestWorkoutSessionModel:
    def test_create_basic_session(self, session):
        ws = WorkoutSessionFactory()
        session.add(ws)
        session.commit()

        assert ws.id is not None
        assert ws.user is not None
        assert ws.status == "PENDING"

    def test_unique_session_per_user_per_day(self, session):
        date = datetime.date.today()

        ws1 = WorkoutSessionFactory(workout_date=date)
        session.add(ws1)
        session.commit()

        ws2 = WorkoutSessionFactory.build(user=ws1.user, workout_date=date)
        session.add(ws2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_optional_routine_day_link(self, session):
        ws = WorkoutSessionFactory()
        session.add(ws)
        session.commit()

        assert ws.routine_day is not None
