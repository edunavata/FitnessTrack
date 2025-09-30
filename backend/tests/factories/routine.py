"""Factory Boy definitions for routine templates and exercises."""

from __future__ import annotations

from app.models.routine import Routine, RoutineExercise

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.user import UserFactory


class RoutineFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.Routine` instances."""

    class Meta:
        model = Routine

    id = None
    user = factory.SubFactory(UserFactory)  # sets user_id automatically
    name = factory.Sequence(lambda n: f"Routine {n}")
    notes = factory.Faker("sentence", nb_words=8)


class RoutineExerciseFactory(BaseFactory):
    """Build :class:`app.models.routine.RoutineExercise` prescriptions."""

    class Meta:
        model = RoutineExercise

    id = None
    routine = factory.SubFactory(RoutineFactory)  # sets routine_id automatically
    exercise = factory.SubFactory(ExerciseFactory)  # sets exercise_id automatically

    # Display order within the routine (1-based)
    order = factory.Sequence(lambda n: n + 1)

    # Defaults aligned with model constraints
    target_sets = 3
    target_reps = 10
    target_rpe = None
    rest_sec = 120
