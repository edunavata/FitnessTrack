"""Factory Boy definition for :class:`app.models.exercise_log.ExerciseSetLog`."""

from __future__ import annotations

import datetime

from app.models.exercise_log import ExerciseSetLog

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import (
    RoutineDayExerciseFactory,
    RoutineDayFactory,
    RoutineExerciseSetFactory,
    RoutineFactory,
)
from tests.factories.subject import SubjectFactory
from tests.factories.workout import WorkoutSessionFactory


class ExerciseSetLogFactory(BaseFactory):
    """Build persisted :class:`app.models.exercise_log.ExerciseSetLog`."""

    class Meta:
        model = ExerciseSetLog

    id = None

    # Owner subject
    subject = factory.SubFactory(SubjectFactory)
    subject_id = factory.SelfAttribute("subject.id")

    # Exercise catalog entry
    exercise = factory.SubFactory(ExerciseFactory)

    # Optional relations (default: None to avoid unique collisions in tests)
    session = None

    # Planned set chain (safe to generate by default; no unique date constraint)
    @factory.lazy_attribute
    def planned_set(self):
        routine = RoutineFactory(subject=self.subject)
        day = RoutineDayFactory(routine=routine)
        rde = RoutineDayExerciseFactory(routine_day=day)
        return RoutineExerciseSetFactory(routine_day_exercise=rde)

    # Timing & ordering
    performed_at = factory.LazyFunction(lambda: datetime.datetime.utcnow())
    set_index = factory.Sequence(lambda n: n + 1)
    is_warmup = False
    to_failure = False

    # Actuals
    actual_weight_kg = 80.0
    actual_reps = 10
    actual_rir = 2
    actual_rpe = 8.0
    actual_tempo = "3-1-1-0"
    actual_rest_s = 90
    notes = "Good set"


class ExerciseSetLogWithSessionFactory(ExerciseSetLogFactory):
    """Same as ExerciseSetLogFactory but ensures a unique WorkoutSession date."""

    # Ensure workout_date is unique per subject (offset by set_index)
    @factory.lazy_attribute
    def session(self):
        workout_date = self.performed_at.date() + datetime.timedelta(days=self.set_index)
        return WorkoutSessionFactory(subject=self.subject, workout_date=workout_date)
