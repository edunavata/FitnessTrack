"""Unit tests for the `Exercise` model."""

from __future__ import annotations

import pytest
from app.models.exercise import Exercise, MuscleGroup
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise import ExerciseFactory


class TestExerciseModel:
    """Tests for Exercise domain logic."""

    @pytest.mark.unit
    def test_create_basic_exercise(self, session):
        """Factory should create a valid exercise with defaults."""
        e = ExerciseFactory()
        session.add(e)
        session.flush()

        assert e.id is not None
        assert isinstance(e.muscle_group, MuscleGroup)
        assert e.is_unilateral in (True, False)
        assert e.created_at is not None
        assert e.updated_at is not None

    @pytest.mark.unit
    def test_name_unique(self, session):
        """Exercise name should be unique."""
        _ = ExerciseFactory(name="Squat", muscle_group=MuscleGroup.QUADS)
        session.flush()

        session.add(Exercise(name="Squat", muscle_group=MuscleGroup.QUADS))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_muscle_group_required(self, session):
        """muscle_group must not be NULL."""
        e = Exercise(name="Deadlift", muscle_group=None)
        session.add(e)
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_is_unilateral_default_false(self, session):
        """is_unilateral should default to False if not set."""
        e = ExerciseFactory(is_unilateral=None)  # factory override
        session.add(e)
        session.flush()
        assert e.is_unilateral is False
