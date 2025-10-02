"""Factory Boy definitions for routine planning models."""

from __future__ import annotations

from app.models.routine import (
    Routine,
    RoutineDay,
    RoutineDayExercise,
    RoutineExerciseSet,
)

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.subject import SubjectFactory  # ← switch to Subject


class RoutineFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.Routine` instances."""

    class Meta:
        model = Routine

    id = None
    subject = factory.SubFactory(SubjectFactory)  # ← was UserFactory
    subject_id = factory.SelfAttribute("subject.id")
    name = factory.Sequence(lambda n: f"Routine {n}")
    description = "Basic routine"
    is_active = True


class RoutineDayFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.RoutineDay` instances."""

    class Meta:
        model = RoutineDay

    id = None
    routine = factory.SubFactory(RoutineFactory)
    day_index = factory.Sequence(lambda n: n + 1)
    is_rest = False
    title = factory.LazyAttribute(lambda o: f"Day {o.day_index}")


class RoutineDayExerciseFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.RoutineDayExercise` instances."""

    class Meta:
        model = RoutineDayExercise

    id = None
    routine_day = factory.SubFactory(RoutineDayFactory)
    exercise = factory.SubFactory(ExerciseFactory)
    position = factory.Sequence(lambda n: n + 1)


class RoutineExerciseSetFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.RoutineExerciseSet` instances."""

    class Meta:
        model = RoutineExerciseSet

    id = None
    routine_day_exercise = factory.SubFactory(RoutineDayExerciseFactory)
    set_index = factory.Sequence(lambda n: n + 1)
    is_warmup = False
    to_failure = False
    target_reps = 10
