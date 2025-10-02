"""Factory Boy definition for :class:`app.models.cycle.Cycle`."""

from __future__ import annotations

from app.models.cycle import Cycle

import factory
from tests.factories import BaseFactory
from tests.factories.routine import RoutineFactory


class CycleFactory(BaseFactory):
    """Build persisted :class:`app.models.cycle.Cycle`."""

    class Meta:
        model = Cycle

    id = None
    routine = factory.SubFactory(RoutineFactory)
    # user derives from routine.user by default; keep them in sync:
    user = factory.SelfAttribute("routine.user")
    cycle_number = factory.Sequence(lambda n: n + 1)
    started_on = None
    ended_on = None
    notes = "Cycle notes"
