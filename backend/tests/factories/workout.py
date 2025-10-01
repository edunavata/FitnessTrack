"""Factory Boy definition for WorkoutSession."""

from __future__ import annotations

import datetime

from app.models.workout import WorkoutSession

import factory
from tests.factories import BaseFactory
from tests.factories.routine import RoutineDayFactory
from tests.factories.user import UserFactory


class WorkoutSessionFactory(BaseFactory):
    """Build persisted :class:`app.models.workout.WorkoutSession`."""

    class Meta:
        model = WorkoutSession

    id = None
    user = factory.SubFactory(UserFactory)
    workout_date = factory.LazyFunction(lambda: datetime.date.today())
    status = "PENDING"
    location = "Gym A"
    perceived_fatigue = 7
    bodyweight_kg = 80.0
    notes = "Good session"

    # optional relation
    routine_day = factory.SubFactory(RoutineDayFactory)
