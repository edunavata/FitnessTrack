from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.repositories.base import Pagination
from app.repositories.workout import WorkoutSessionRepository
from tests.factories.cycle import CycleFactory
from tests.factories.routine import RoutineFactory
from tests.factories.subject import SubjectFactory

UTC = UTC


class TestWorkoutSessionRepository:
    @pytest.fixture()
    def repo(self) -> WorkoutSessionRepository:
        return WorkoutSessionRepository()

    def _dt(self, y, m, d, h=10, mi=0, s=0):
        return datetime(y, m, d, h, mi, s, tzinfo=UTC)

    def test_create_and_get_by_unique(self, repo, session):
        s = SubjectFactory()
        session.add(s)
        session.flush()

        ws = repo.create_session(subject_id=s.id, workout_date=self._dt(2024, 1, 1, 9))
        assert ws.id is not None and ws.status == "PENDING"

        got = repo.get_by_unique(s.id, self._dt(2024, 1, 1, 9))
        assert got is not None and got.id == ws.id

    def test_upsert_by_date_insert_then_update(self, repo, session):
        s = SubjectFactory()
        session.add(s)
        session.flush()

        d = self._dt(2024, 2, 1, 18)

        # insert
        ws1 = repo.upsert_by_date(
            subject_id=s.id, workout_date=d, location="Home", perceived_fatigue=5
        )
        assert ws1.id is not None and ws1.location == "Home"

        # update
        ws2 = repo.upsert_by_date(
            subject_id=s.id, workout_date=d, status="COMPLETED", bodyweight_kg=80.5
        )
        assert ws2.id == ws1.id
        assert ws2.status == "COMPLETED"
        assert ws2.bodyweight_kg == 80.5

    def test_attach_to_cycle_validator(self, repo, session):
        s1 = SubjectFactory()
        s2 = SubjectFactory()
        r = RoutineFactory(owner=s1, name="Block")
        c = CycleFactory(subject=s1, routine=r, cycle_number=1)

        session.add_all([s1, s2, r, c])
        session.flush()

        ws = repo.create_session(subject_id=s1.id, workout_date=self._dt(2024, 3, 1, 9))
        # OK: same subject
        repo.attach_to_cycle(ws.id, c.id)
        assert ws.cycle_id == c.id

        # Now mismatch: session belongs to s1; cycle of s2 → should raise
        c_mismatch = CycleFactory(subject=s2, routine=r, cycle_number=2)
        session.add(c_mismatch)
        session.flush()
        with pytest.raises(ValueError):
            repo.attach_to_cycle(ws.id, c_mismatch.id)

    def test_list_for_subject_and_pagination(self, repo, session):
        s = SubjectFactory()
        session.add(s)
        session.flush()

        base = self._dt(2024, 4, 1, 9)
        for i in range(5):
            repo.create_session(subject_id=s.id, workout_date=base + timedelta(days=i))

        # range [Apr 2, Apr 4], newest first
        rows = repo.list_for_subject(
            s.id, date_from=date(2024, 4, 2), date_to=date(2024, 4, 4), sort=["-workout_date"]
        )
        assert [r.workout_date.date() for r in rows] == [
            date(2024, 4, 4),
            date(2024, 4, 3),
            date(2024, 4, 2),
        ]

        # paginate
        page1 = repo.paginate_for_subject(
            Pagination(page=1, limit=2, sort=["workout_date"]), subject_id=s.id, with_total=True
        )
        assert page1.total == 5
        assert len(page1.items) == 2
        assert [x.workout_date.date() for x in page1.items] == [date(2024, 4, 1), date(2024, 4, 2)]

    def test_list_for_cycle_sorted(self, repo, session):
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="Plan")
        c = CycleFactory(subject=s, routine=r, cycle_number=1)
        session.add_all([s, r, c])
        session.flush()

        ws1 = repo.create_session(
            subject_id=s.id, workout_date=self._dt(2024, 5, 1, 9), cycle_id=c.id
        )
        ws2 = repo.create_session(
            subject_id=s.id, workout_date=self._dt(2024, 5, 2, 9), cycle_id=c.id
        )

        rows = repo.list_for_cycle(c.id, sort=["-workout_date"])
        assert [w.id for w in rows] == [ws2.id, ws1.id]

    def test_mark_completed(self, repo, session):
        s = SubjectFactory()
        session.add(s)
        session.flush()

        ws = repo.create_session(subject_id=s.id, workout_date=self._dt(2024, 6, 1, 9))
        repo.mark_completed(ws.id)
        assert ws.status == "COMPLETED"
