"""Unit tests for ExerciseSetLog model."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise import ExerciseFactory
from tests.factories.exercise_log import (
    ExerciseSetLogFactory,
    ExerciseSetLogWithSessionFactory,
)
from tests.factories.routine import (
    RoutineDayExerciseFactory,
    RoutineDayFactory,
    RoutineExerciseSetFactory,
    RoutineFactory,
)
from tests.factories.subject import SubjectFactory
from tests.factories.workout import WorkoutSessionFactory


class TestExerciseSetLogModel:
    def test_create_basic_log(self, session):
        esl = ExerciseSetLogFactory()  # session is optional by default
        session.add(esl)
        session.commit()

        assert esl.id is not None
        assert esl.subject is not None
        assert esl.exercise is not None
        # session may be None by default; planned_set is present
        assert esl.planned_set is not None

    def test_unique_per_subject_exercise_time_set_index(self, session):
        s = SubjectFactory()
        ex = ExerciseFactory()
        ts = datetime.datetime.utcnow()

        esl1 = ExerciseSetLogFactory(subject=s, exercise=ex, performed_at=ts, set_index=1)
        session.add(esl1)
        session.commit()

        esl2 = ExerciseSetLogFactory.build(subject=s, exercise=ex, performed_at=ts, set_index=1)
        session.add(esl2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_same_timestamp_allowed_for_different_subjects(self, session):
        ex = ExerciseFactory()
        ts = datetime.datetime.utcnow()

        esl1 = ExerciseSetLogFactory(subject=SubjectFactory(), exercise=ex, performed_at=ts)
        esl2 = ExerciseSetLogFactory(subject=SubjectFactory(), exercise=ex, performed_at=ts)

        session.add_all([esl1, esl2])
        session.commit()

        assert esl1.id != esl2.id

    def test_session_must_match_subject(self, session):
        s1 = SubjectFactory()
        s2 = SubjectFactory()

        ws = WorkoutSessionFactory(subject=s2)  # different subject
        esl = ExerciseSetLogFactory.build(subject=s1, session=ws)

        session.add_all([ws, esl])
        with pytest.raises(ValueError):
            session.flush()
        session.rollback()

    def test_planned_set_can_belong_to_other_subject(self, session):
        """Now allowed: planned_set may come from another subject's routine if shared."""
        s1 = SubjectFactory()
        s2 = SubjectFactory()

        routine = RoutineFactory(owner=s2)
        day = RoutineDayFactory(routine=routine)
        rde = RoutineDayExerciseFactory(routine_day=day)
        pes = RoutineExerciseSetFactory(routine_day_exercise=rde)

        # esl subject != routine owner → now valid
        esl = ExerciseSetLogFactory.build(subject=s1, planned_set=pes)

        session.add(esl)
        session.commit()

        assert esl.id is not None
        assert esl.planned_set_id == pes.id

    def test_factory_with_session_assigns_unique_date(self, session):
        esl1 = ExerciseSetLogWithSessionFactory()
        esl2 = ExerciseSetLogWithSessionFactory(subject=esl1.subject)  # same subject, shifted date

        session.add_all([esl1, esl2])
        session.commit()

        assert esl1.session.workout_date != esl2.session.workout_date
