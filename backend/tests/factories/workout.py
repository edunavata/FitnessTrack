"""Factory Boy definitions for workout tracking models."""

from __future__ import annotations

from decimal import Decimal

from app.models.workout import Workout, WorkoutExercise, WorkoutSet

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.user import UserFactory


class WorkoutFactory(BaseFactory):
    """Build persisted :class:`app.models.workout.Workout` instances."""

    class Meta:
        model = Workout

    id = None
    user = factory.SubFactory(UserFactory)  # sets user_id
    # Routine is optional; override in tests that need an explicit association.
    # date -> allow the model default (date.today) to populate the field.
    duration_min = None
    notes = factory.Faker("sentence", nb_words=8)


class WorkoutExerciseFactory(BaseFactory):
    """Build :class:`app.models.workout.WorkoutExercise` instances."""

    class Meta:
        model = WorkoutExercise

    id = None
    workout = factory.SubFactory(WorkoutFactory)  # sets workout_id
    exercise = factory.SubFactory(ExerciseFactory)  # sets exercise_id
    order = factory.Sequence(lambda n: n + 1)  # 1-based
    notes = factory.Faker("sentence", nb_words=6)


class WorkoutSetFactory(BaseFactory):
    """Build :class:`app.models.workout.WorkoutSet` instances."""

    class Meta:
        model = WorkoutSet

    id = None
    workout_exercise = factory.SubFactory(WorkoutExerciseFactory)  # sets workout_exercise_id
    set_index = factory.Sequence(lambda n: n + 1)  # 1-based
    reps = 10
    weight_kg = factory.LazyFunction(lambda: Decimal("60.0"))
    rpe = None
    rir = None
    time_sec = None
