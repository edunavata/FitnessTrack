"""Unit tests for ``ExerciseSetLogRepository`` pagination and CRUD helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.repositories.base import Pagination
from app.repositories.exercise_set_log import ExerciseSetLogRepository
from tests.factories.exercise import ExerciseFactory
from tests.factories.subject import SubjectFactory
from tests.factories.workout import WorkoutSessionFactory

UTC = UTC


class TestExerciseSetLogRepository:
    """Validate persistence patterns for exercise set logs."""
    @pytest.fixture()
    def repo(self) -> ExerciseSetLogRepository:
        return ExerciseSetLogRepository()

    def _dt(self, y, m, d, h=10, mi=0, s=0):
        return datetime(y, m, d, h, mi, s, tzinfo=UTC)

    def test_create_and_validator_session_subject_match(self, repo, session):
        """Creating with a session from another subject should raise via validator."""
        s1 = SubjectFactory()
        s2 = SubjectFactory()
        ex = ExerciseFactory()
        ws_other = WorkoutSessionFactory(subject=s2)

        session.add_all([s1, s2, ex, ws_other])
        session.flush()

        # OK without session
        row = repo.create_log(
            subject_id=s1.id,
            exercise_id=ex.id,
            performed_at=self._dt(2024, 1, 1),
            set_index=1,
        )
        assert row.id is not None

        # Mismatch: subject_id != session.subject_id → validator ValueError
        with pytest.raises(ValueError):
            repo.create_log(
                subject_id=s1.id,
                exercise_id=ex.id,
                performed_at=self._dt(2024, 1, 1, 10, 5),
                set_index=1,
                session_id=ws_other.id,
            )

    def test_upsert_log_insert_then_update(self, repo, session):
        """Insert a log and update the same composite key with new values."""
        s = SubjectFactory()
        ex = ExerciseFactory()
        session.add_all([s, ex])
        session.flush()

        key_dt = self._dt(2024, 2, 1, 9, 0, 0)

        # Insert
        row1 = repo.upsert_log(
            subject_id=s.id,
            exercise_id=ex.id,
            performed_at=key_dt,
            set_index=1,
            actual_weight_kg=100.0,
            actual_reps=5,
        )
        assert row1.id is not None
        assert row1.actual_weight_kg == 100.0
        assert row1.actual_reps == 5

        # Update on same key
        row2 = repo.upsert_log(
            subject_id=s.id,
            exercise_id=ex.id,
            performed_at=key_dt,
            set_index=1,
            actual_weight_kg=102.5,
            actual_reps=4,
            notes="AMRAP-ish",
        )
        assert row2.id == row1.id
        assert row2.actual_weight_kg == 102.5
        assert row2.actual_reps == 4
        assert row2.notes == "AMRAP-ish"

    def test_list_for_subject_date_range_and_filters(self, repo, session):
        """List subject logs filtered by date range, exercise, and ordering."""
        s = SubjectFactory()
        ex1 = ExerciseFactory()
        ex2 = ExerciseFactory()
        session.add_all([s, ex1, ex2])
        session.flush()

        # Seed 4 logs across two exercises and days
        repo.create_log(
            subject_id=s.id, exercise_id=ex1.id, performed_at=self._dt(2024, 1, 1, 10), set_index=1
        )
        repo.create_log(
            subject_id=s.id, exercise_id=ex1.id, performed_at=self._dt(2024, 1, 2, 11), set_index=1
        )
        repo.create_log(
            subject_id=s.id, exercise_id=ex2.id, performed_at=self._dt(2024, 1, 2, 12), set_index=1
        )
        repo.create_log(
            subject_id=s.id, exercise_id=ex2.id, performed_at=self._dt(2024, 1, 3, 10), set_index=1
        )

        # Range [Jan 2, Jan 3], only ex2, newest first
        rows = repo.list_for_subject(
            subject_id=s.id,
            date_from=date(2024, 1, 2),
            date_to=date(2024, 1, 3),
            exercise_id=ex2.id,
            sort=["-performed_at"],
        )
        dts = [r.performed_at.date() for r in rows]
        assert dts == [date(2024, 1, 3), date(2024, 1, 2)]

    def test_paginate_for_subject(self, repo, session):
        """Paginate subject logs and verify totals and item counts per page."""
        s = SubjectFactory()
        ex = ExerciseFactory()
        session.add_all([s, ex])
        session.flush()

        base_dt = self._dt(2024, 3, 1, 8)
        # Create 5 logs same exercise, increasing time and set_index
        for i in range(5):
            repo.create_log(
                subject_id=s.id,
                exercise_id=ex.id,
                performed_at=base_dt + timedelta(minutes=i),
                set_index=1,
            )

        page1 = repo.paginate_for_subject(
            Pagination(page=1, limit=2, sort=["performed_at"]),
            subject_id=s.id,
            with_total=True,
        )
        assert page1.total == 5
        assert len(page1.items) == 2

        page2 = repo.paginate_for_subject(
            Pagination(page=2, limit=2, sort=["performed_at"]),
            subject_id=s.id,
            with_total=False,
        )
        assert page2.total == 0
        assert len(page2.items) == 2

    def test_list_for_session_sorted(self, repo, session):
        """List logs for a session sorted by time and set index."""
        s = SubjectFactory()
        ex = ExerciseFactory()
        ws = WorkoutSessionFactory(subject=s)
        session.add_all([s, ex, ws])
        session.flush()

        repo.create_log(
            subject_id=s.id,
            exercise_id=ex.id,
            performed_at=self._dt(2024, 4, 1, 10),
            set_index=2,
            session_id=ws.id,
        )
        repo.create_log(
            subject_id=s.id,
            exercise_id=ex.id,
            performed_at=self._dt(2024, 4, 1, 10),
            set_index=1,
            session_id=ws.id,
        )

        rows = repo.list_for_session(ws.id, sort=["performed_at", "set_index"])
        assert [r.set_index for r in rows] == [1, 2]

    def test_latest_for_subject_exercise(self, repo, session):
        """Retrieve the latest log for a subject/exercise using ordering rules."""
        s = SubjectFactory()
        ex = ExerciseFactory()
        session.add_all([s, ex])
        session.flush()

        repo.create_log(
            subject_id=s.id, exercise_id=ex.id, performed_at=self._dt(2024, 5, 1, 10), set_index=1
        )
        repo.create_log(
            subject_id=s.id, exercise_id=ex.id, performed_at=self._dt(2024, 5, 2, 10), set_index=1
        )
        repo.create_log(
            subject_id=s.id, exercise_id=ex.id, performed_at=self._dt(2024, 5, 2, 10), set_index=2
        )

        latest = repo.latest_for_subject_exercise(s.id, ex.id)
        assert latest is not None
        # Expect 2024-05-02 10:00 set_index=2 (same datetime, higher set_index)
        assert latest.performed_at.date() == date(2024, 5, 2)
        assert latest.set_index == 2
