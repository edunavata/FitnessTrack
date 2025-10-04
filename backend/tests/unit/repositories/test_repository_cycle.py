"""Unit tests for ``CycleRepository`` persistence helpers."""

from __future__ import annotations

from datetime import date

import pytest
from app.repositories.base import Pagination
from app.repositories.cycle import CycleRepository
from tests.factories.cycle import CycleFactory
from tests.factories.routine import RoutineFactory
from tests.factories.subject import SubjectFactory


class TestCycleRepository:
    """Validate ``CycleRepository`` behaviours for numbering and listings."""

    @pytest.fixture()
    def repo(self) -> CycleRepository:
        return CycleRepository()

    def test_create_and_get_by_unique(self, repo, session):
        """Given a created cycle, when fetched by unique key then it is returned."""
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="Mesocycle A")
        session.add_all([s, r])
        session.flush()

        c1 = repo.create_cycle(subject_id=s.id, routine_id=r.id)  # auto cycle_number=1
        assert c1.cycle_number == 1

        c_got = repo.get_by_unique(s.id, r.id, 1)
        assert c_got is not None and c_got.id == c1.id

    def test_next_cycle_number_and_ensure(self, repo, session):
        """Ensure the repository increments cycle numbers and backfills missing ones."""
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="Plan")
        session.add_all([s, r])
        session.flush()

        # Seed one cycle with number 2 explicitly
        c = CycleFactory(subject=s, routine=r, cycle_number=2)
        session.add(c)
        session.flush()

        nxt = repo.next_cycle_number(s.id, r.id)
        assert nxt == 3

        # ensure sets cycle_number if missing/0
        c2 = CycleFactory.build(subject=s, routine=r, cycle_number=0)
        session.add(c2)
        with session.no_autoflush:
            repo.ensure_cycle_number(c2)
        session.flush()

        assert c2.cycle_number == 3  # after ensuring

    def test_start_and_finish_cycle(self, repo, session):
        """Start and finish dates persist when invoking lifecycle helpers."""
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="PPL")
        session.add_all([s, r])
        session.flush()

        c = repo.create_cycle(subject_id=s.id, routine_id=r.id, cycle_number=1)
        repo.start_cycle(c.id, date(2024, 1, 10))
        assert c.started_on == date(2024, 1, 10)

        repo.finish_cycle(c.id, date(2024, 2, 10))
        assert c.ended_on == date(2024, 2, 10)

    def test_list_by_subject_and_routine_and_sorting(self, repo, session):
        """List cycles ordered by cycle number within subject and routine scopes."""
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="Block")
        session.add_all([s, r])
        session.flush()

        # 3 cycles
        repo.create_cycle(subject_id=s.id, routine_id=r.id, cycle_number=1)
        repo.create_cycle(subject_id=s.id, routine_id=r.id, cycle_number=2)
        repo.create_cycle(subject_id=s.id, routine_id=r.id, cycle_number=3)

        by_subject = repo.list_by_subject(s.id, sort=["-cycle_number"])
        assert [c.cycle_number for c in by_subject] == [3, 2, 1]

        by_routine = repo.list_by_routine(r.id, sort=["cycle_number"])
        assert [c.cycle_number for c in by_routine] == [1, 2, 3]

    def test_paginate_for_subject(self, repo, session):
        """Paginate cycles for a subject yielding deterministic totals and items."""
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="Meso")
        session.add_all([s, r])
        session.flush()

        for i in range(1, 6):
            repo.create_cycle(subject_id=s.id, routine_id=r.id, cycle_number=i)

        page1 = repo.paginate_for_subject(
            Pagination(page=1, limit=2, sort=["cycle_number"]),
            subject_id=s.id,
            with_total=True,
        )
        assert page1.total == 5
        assert [c.cycle_number for c in page1.items] == [1, 2]

        page2 = repo.paginate_for_subject(
            Pagination(page=2, limit=2, sort=["cycle_number"]),
            subject_id=s.id,
            with_total=False,
        )
        assert page2.total == 0
        assert [c.cycle_number for c in page2.items] == [3, 4]
