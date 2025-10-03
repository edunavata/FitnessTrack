"""Factory Boy definition for :class:`app.models.cycle.Cycle`."""

from __future__ import annotations

from app.models.cycle import Cycle

import factory
from tests.factories import BaseFactory
from tests.factories.routine import RoutineFactory
from tests.factories.subject import SubjectFactory


class CycleFactory(BaseFactory):
    """Build persisted :class:`app.models.cycle.Cycle`."""

    class Meta:
        model = Cycle

    id = None

    # Subject executing the cycle
    subject = factory.SubFactory(SubjectFactory)
    subject_id = factory.SelfAttribute("subject.id")

    # Routine: ensure it belongs to the same subject by default
    routine = factory.LazyAttribute(lambda o: RoutineFactory(owner=o.subject))
    routine_id = factory.SelfAttribute("routine.id")

    cycle_number = factory.Sequence(lambda n: n + 1)
    started_on = None
    ended_on = None
    notes = "Cycle notes"
