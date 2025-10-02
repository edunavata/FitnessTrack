"""Factory Boy definition for :class:`app.models.workout.WorkoutSession`."""

from __future__ import annotations

import datetime

from app.models.workout import WorkoutSession

import factory
from tests.factories import BaseFactory
from tests.factories.routine import RoutineDayFactory, RoutineFactory
from tests.factories.subject import SubjectFactory


class WorkoutSessionFactory(BaseFactory):
    """Build persisted :class:`app.models.workout.WorkoutSession`."""

    class Meta:
        model = WorkoutSession

    id = None
    subject = factory.SubFactory(SubjectFactory)
    subject_id = factory.SelfAttribute("subject.id")

    workout_date = factory.LazyFunction(lambda: datetime.date.today())
    status = "PENDING"
    location = "Gym A"
    perceived_fatigue = 7
    bodyweight_kg = 80.0
    notes = "Good session"

    # By default, attach a RoutineDay that belongs to the same subject (via Routine)
    @factory.lazy_attribute
    def routine_day(self):
        routine = RoutineFactory(subject=self.subject)
        return RoutineDayFactory(routine=routine)
