"""Factory Boy definitions for routine planning models."""

from __future__ import annotations

from app.models.routine import (
    Routine,
    RoutineDay,
    RoutineDayExercise,
    RoutineExerciseSet,
    SubjectRoutine,
)

import factory
from tests.factories import BaseFactory
from tests.factories.exercise import ExerciseFactory
from tests.factories.subject import SubjectFactory


class RoutineFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.Routine` instances."""

    class Meta:
        model = Routine

    id = None

    # Owner subject
    owner = factory.SubFactory(SubjectFactory)
    owner_subject_id = factory.SelfAttribute("owner.id")

    name = factory.Sequence(lambda n: f"Routine {n}")
    description = "Basic routine"
    is_public = False  # default: routines are private


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


class SubjectRoutineFactory(BaseFactory):
    """Build persisted :class:`app.models.routine.SubjectRoutine` instances."""

    class Meta:
        model = SubjectRoutine

    id = None
    subject = factory.SubFactory(SubjectFactory)
    routine = factory.SubFactory(RoutineFactory, owner=factory.SelfAttribute("..subject"))

    # Campos adicionales de la relación
    is_active = False
