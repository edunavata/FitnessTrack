"""Unit tests for ExerciseSetLog model."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise_log import ExerciseSetLogFactory


class TestExerciseSetLog:
    def test_create_basic_log(self, session):
        log = ExerciseSetLogFactory()
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.user is not None
        assert log.exercise is not None
        assert log.session is not None
        assert log.set_index == 1

    def test_unique_constraint(self, session):
        ts = datetime.datetime.utcnow()

        log1 = ExerciseSetLogFactory(performed_at=ts, set_index=1)
        session.add(log1)
        session.commit()

        # Same user, exercise, time, set_index → must fail
        log2 = ExerciseSetLogFactory.build(
            user=log1.user,
            exercise=log1.exercise,
            performed_at=ts,
            set_index=1,
        )
        session.add(log2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_optional_links(self, session):
        log = ExerciseSetLogFactory(session=None, planned_set=None)
        session.add(log)
        session.commit()

        assert log.session is None
        assert log.planned_set is None
