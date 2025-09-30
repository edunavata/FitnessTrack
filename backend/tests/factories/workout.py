"""Factories for Workout, WorkoutExercise, and WorkoutSet models."""

from __future__ import annotations

from decimal import Decimal

from app.models.workout import Workout, WorkoutExercise, WorkoutSet

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.user import UserFactory


class WorkoutFactory(BaseFactory):
    """Factory for the `Workout` model."""

    class Meta:
        model = Workout

    id = None
    user = factory.SubFactory(UserFactory)  # sets user_id
    # routine is optional; si quieres cubrirlo en casos concretos:
    # routine = factory.SubFactory(RoutineFactory)
    # date -> dejamos que lo ponga el default del modelo (date.today)
    duration_min = None
    notes = factory.Faker("sentence", nb_words=8)


class WorkoutExerciseFactory(BaseFactory):
    """Factory for the `WorkoutExercise` model."""

    class Meta:
        model = WorkoutExercise

    id = None
    workout = factory.SubFactory(WorkoutFactory)  # sets workout_id
    exercise = factory.SubFactory(ExerciseFactory)  # sets exercise_id
    order = factory.Sequence(lambda n: n + 1)  # 1-based
    notes = factory.Faker("sentence", nb_words=6)


class WorkoutSetFactory(BaseFactory):
    """Factory for the `WorkoutSet` model."""

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
