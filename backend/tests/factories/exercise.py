"""Factories for Exercise-related models."""

from __future__ import annotations

from app.models.exercise import Exercise, MuscleGroup

import factory
from tests.factories import BaseFactory


class ExerciseFactory(BaseFactory):
    """Factory for the `Exercise` model."""

    class Meta:
        model = Exercise

    id = None
    name = factory.Sequence(lambda n: f"Exercise{n}")
    muscle_group = factory.Iterator(list(MuscleGroup))
    is_unilateral = False
    notes = factory.Faker("sentence", nb_words=6)
