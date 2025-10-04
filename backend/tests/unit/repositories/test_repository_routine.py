"""Unit tests for routine repositories covering days, sets, and saves."""

from __future__ import annotations

from datetime import UTC

import pytest
from app.repositories.base import Pagination
from app.repositories.routine import RoutineRepository, SubjectRoutineRepository
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import RoutineFactory
from tests.factories.subject import SubjectFactory

UTC = UTC


class TestRoutineRepository:
    """Ensure ``RoutineRepository`` handles nested structures consistently."""
    @pytest.fixture()
    def repo(self) -> RoutineRepository:
        return RoutineRepository()

    def test_list_by_owner_and_public(self, repo, session):
        """List routines by owner and retrieve all public routines."""
        owner = SubjectFactory()
        other = SubjectFactory()
        r1 = RoutineFactory(owner=owner, name="PPL", is_public=True)
        r2 = RoutineFactory(owner=owner, name="Hypertrophy", is_public=False)
        r3 = RoutineFactory(owner=other, name="Other", is_public=True)
        session.add_all([owner, other, r1, r2, r3])
        session.flush()

        by_owner = repo.list_by_owner(owner.id, sort=["name"])
        assert [r.name for r in by_owner] == ["Hypertrophy", "PPL"]

        public = repo.list_public(sort=["name"])
        assert [r.name for r in public] == ["Other", "PPL"]

    def test_add_day_auto_index_and_unique(self, repo, session):
        """Add routine days auto-indexing sequential positions."""
        owner = SubjectFactory()
        r = RoutineFactory(owner=owner, name="Plan A")
        session.add_all([owner, r])
        session.flush()

        d1 = repo.add_day(r.id)  # index=1
        d2 = repo.add_day(r.id)  # index=2
        assert d1.day_index == 1 and d2.day_index == 2

        # adding explicit index works
        d3 = repo.add_day(r.id, day_index=5)
        assert d3.day_index == 5

    def test_add_exercise_to_day_append_position(self, repo, session):
        """Append exercises to a routine day preserving positional order."""
        owner = SubjectFactory()
        r = RoutineFactory(owner=owner, name="Plan B")
        e1 = ExerciseFactory(name="Bench", slug="bench")
        e2 = ExerciseFactory(name="Row", slug="row")
        session.add_all([owner, r, e1, e2])
        session.flush()

        day = repo.add_day(r.id)  # index 1
        de1 = repo.add_exercise_to_day(day.id, e1.id)  # pos 1
        de2 = repo.add_exercise_to_day(day.id, e2.id)  # pos 2

        assert (de1.position, de2.position) == (1, 2)

    def test_upsert_set_insert_then_update(self, repo, session):
        """Insert a planned set and update it via composite key."""
        owner = SubjectFactory()
        r = RoutineFactory(owner=owner, name="Plan C")
        e = ExerciseFactory(name="Squat", slug="squat")
        session.add_all([owner, r, e])
        session.flush()

        day = repo.add_day(r.id)
        de = repo.add_exercise_to_day(day.id, e.id)

        # insert
        s1 = repo.upsert_set(de.id, 1, target_reps=8, target_weight_kg=100.0, is_warmup=False)
        assert s1.id is not None and s1.target_reps == 8

        # update on same key
        s2 = repo.upsert_set(de.id, 1, target_reps=10, to_failure=True)
        assert s2.id == s1.id
        assert s2.target_reps == 10
        assert s2.to_failure is True

    def test_paginate_public(self, repo, session):
        """Paginate public routines and report deterministic totals."""
        owner = SubjectFactory()
        session.add(owner)
        session.flush()
        # 3 public routines
        for i in range(3):
            session.add(RoutineFactory.build(owner=owner, name=f"P{i}", is_public=True))
        session.flush()

        page = repo.paginate_public(Pagination(page=1, limit=2, sort=["name"]), with_total=True)
        assert page.total == 3
        assert len(page.items) == 2


class TestSubjectRoutineRepository:
    """Verify ``SubjectRoutineRepository`` manages saved routines idempotently."""
    @pytest.fixture()
    def repo(self) -> SubjectRoutineRepository:
        return SubjectRoutineRepository()

    def test_save_remove_and_set_active(self, repo, session):
        """Save a routine, toggle its active flag, and remove it cleanly."""
        s = SubjectFactory()
        r = RoutineFactory(owner=s, name="X", is_public=True)
        other = SubjectFactory()
        session.add_all([s, r, other])
        session.flush()

        # other saves r
        link1 = repo.save(other.id, r.id)
        assert link1.id is not None and link1.is_active is False

        # idempotent save
        link2 = repo.save(other.id, r.id)
        assert link2.id == link1.id

        # activate
        repo.set_active(other.id, r.id, True)
        assert repo.list_saved_by_subject(other.id)[0].is_active is True

        # remove
        removed = repo.remove(other.id, r.id)
        assert removed == 1
        assert repo.list_saved_by_subject(other.id) == []
