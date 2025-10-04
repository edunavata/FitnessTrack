"""Unit tests for ExerciseSecondaryMuscle model."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise_secondary import ExerciseSecondaryMuscleFactory


class TestExerciseSecondaryMuscle:
    def test_create_basic_secondary_muscle(self, session):
        esm = ExerciseSecondaryMuscleFactory(muscle="BACK")
        session.add(esm)
        session.commit()

        assert esm.exercise is not None
        assert esm.muscle == "BACK"

    def test_unique_constraint(self, session):
        esm1 = ExerciseSecondaryMuscleFactory(muscle="GLUTES")
        session.add(esm1)
        session.commit()

        # same exercise + same muscle → must fail
        esm2 = ExerciseSecondaryMuscleFactory.build(exercise=esm1.exercise, muscle="GLUTES")
        session.add(esm2)

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
