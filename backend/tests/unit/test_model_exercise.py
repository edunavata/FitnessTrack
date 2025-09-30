"""Unit tests covering constraints and defaults on the Exercise model."""

from __future__ import annotations

import pytest
from app.models.exercise import Exercise, MuscleGroup
from sqlalchemy.exc import IntegrityError
from tests.factories.exercise import ExerciseFactory


class TestExerciseModel:
    """Tests for Exercise domain logic."""

    @pytest.mark.unit
    def test_create_basic_exercise(self, session):
        """Arrange an exercise via the factory, insert it, and assert defaults persist."""
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
        """Arrange two exercises sharing a name, flush, and expect an integrity error."""
        _ = ExerciseFactory(name="Squat", muscle_group=MuscleGroup.QUADS)
        session.flush()

        session.add(Exercise(name="Squat", muscle_group=MuscleGroup.QUADS))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_muscle_group_required(self, session):
        """Arrange an exercise missing ``muscle_group``, flush, and assert the DB rejects it."""
        e = Exercise(name="Deadlift", muscle_group=None)
        session.add(e)
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_is_unilateral_default_false(self, session):
        """Confirm default unilateral flag persists.

        Arrange with a factory exercise using the default field.
        Act by flushing the session.
        Assert the stored value resolves to ``False``.
        """
        e = ExerciseFactory(is_unilateral=None)  # factory override
        session.add(e)
        session.flush()
        assert e.is_unilateral is False
