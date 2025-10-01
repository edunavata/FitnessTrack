"""Factory Boy definition for ExerciseSecondaryMuscle."""

from __future__ import annotations

from app.models.exercise_secondary import ExerciseSecondaryMuscle

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory


class ExerciseSecondaryMuscleFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise_secondary.ExerciseSecondaryMuscle`."""

    class Meta:
        model = ExerciseSecondaryMuscle

    exercise = factory.SubFactory(ExerciseFactory)
    muscle = factory.Iterator(["BACK", "SHOULDERS", "QUADS", "HAMSTRINGS", "GLUTES", "BICEPS"])
