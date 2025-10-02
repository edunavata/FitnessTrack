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

    # Let callers pass a subject; default to a fresh one
    subject = factory.SubFactory(SubjectFactory)
    subject_id = factory.SelfAttribute("subject.id")

    # Ensure the Routine belongs to the SAME subject as the Cycle
    routine = factory.LazyAttribute(lambda o: RoutineFactory(subject=o.subject))

    cycle_number = factory.Sequence(lambda n: n + 1)
    started_on = None
    ended_on = None
    notes = "Cycle notes"
