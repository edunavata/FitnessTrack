"""Factories for Subject, SubjectProfile, and SubjectBodyMetrics."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.models.subject import (
    SexEnum,
    Subject,
    SubjectBodyMetrics,
    SubjectProfile,
)

import factory
from tests.factories import BaseFactory
from tests.factories.user import UserFactory


class SubjectFactory(BaseFactory):
    """Build persisted :class:`app.models.subject.Subject` instances."""

    class Meta:
        model = Subject

    id = None
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    pseudonym = factory.LazyFunction(uuid4)


class SubjectProfileFactory(BaseFactory):
    """Build persisted :class:`app.models.subject.SubjectProfile` instances."""

    class Meta:
        model = SubjectProfile

    id = None
    subject = factory.SubFactory(SubjectFactory)
    subject_id = factory.SelfAttribute("subject.id")
    sex = SexEnum.MALE
    birth_year = 1999
    height_cm = 180
    dominant_hand = "right"


class SubjectBodyMetricsFactory(BaseFactory):
    """Build persisted :class:`app.models.subject.SubjectBodyMetrics` instances."""

    class Meta:
        model = SubjectBodyMetrics

    id = None
    subject = factory.SubFactory(SubjectFactory)
    subject_id = factory.SelfAttribute("subject.id")
    measured_on = factory.LazyFunction(lambda: date.today())
    weight_kg = 80.5
    bodyfat_pct = 15.2
    resting_hr = 52
    notes = "Morning measurement."
