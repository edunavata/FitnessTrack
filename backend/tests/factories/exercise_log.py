"""Factory Boy definition for ExerciseSetLog."""

from __future__ import annotations

import datetime

from app.models.exercise_log import ExerciseSetLog

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import RoutineExerciseSetFactory
from tests.factories.user import UserFactory
from tests.factories.workout import WorkoutSessionFactory


class ExerciseSetLogFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise_log.ExerciseSetLog`."""

    class Meta:
        model = ExerciseSetLog

    id = None
    user = factory.SubFactory(UserFactory)
    exercise = factory.SubFactory(ExerciseFactory)
    session = factory.SubFactory(WorkoutSessionFactory)
    planned_set = factory.SubFactory(RoutineExerciseSetFactory)

    performed_at = factory.LazyFunction(lambda: datetime.datetime.utcnow())
    set_index = factory.Sequence(lambda n: n + 1)
    is_warmup = False
    to_failure = False
    actual_weight_kg = 80.0
    actual_reps = 10
    actual_rir = 2
    actual_rpe = 8.0
    actual_tempo = "3-1-1-0"
    actual_rest_s = 90
    notes = "Good set"
