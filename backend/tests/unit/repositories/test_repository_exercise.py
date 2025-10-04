"""Unit tests for ``ExerciseRepository`` covering tags and aliases."""

from __future__ import annotations

import pytest
from app.repositories.exercise import ExerciseRepository
from tests.factories.exercise import ExerciseFactory  # you already have it


class TestExerciseRepository:
    """Verify ``ExerciseRepository`` CRUD helpers and tag workflows."""

    @pytest.fixture()
    def repo(self) -> ExerciseRepository:
        return ExerciseRepository()

    def test_get_by_slug(self, repo, session):
        """Retrieve an exercise by slug and ensure eager loading works."""
        e = ExerciseFactory(name="Bench Press", slug="bench-press")
        session.add(e)
        session.flush()

        got = repo.get_by_slug("bench-press")
        assert got is not None
        assert got.id == e.id
        assert got.slug == "bench-press"

    def test_sorting_and_filter_whitelist(self, repo, session):
        """List exercises with whitelist filters and deterministic ordering."""
        e1 = ExerciseFactory(name="A", slug="a", is_active=True)
        e2 = ExerciseFactory(name="B", slug="b", is_active=False)
        session.add_all([e1, e2])
        session.flush()

        # filter by whitelist key
        actives = repo.list(filters={"is_active": True}, sort=["name"])
        assert [x.slug for x in actives] == ["a"]

        # unknown key → ignored; returns both (at least)
        all_items = repo.list(filters={"unknown": 1})
        assert len(all_items) >= 2

        # sorting deterministic (by name then PK tiebreaker)
        items = repo.list(sort=["name"])
        names = [x.name for x in items]
        assert names == sorted(names)

    def test_add_and_remove_alias(self, repo, session):
        """Add aliases idempotently and remove them without duplicates."""
        e = ExerciseFactory(name="Row", slug="row")
        session.add(e)
        session.flush()

        a1 = repo.add_alias(e.id, "Remo con barra")
        assert a1.id is not None
        # idempotent on same alias
        a2 = repo.add_alias(e.id, "Remo con barra")
        assert a2.id == a1.id

        removed = repo.remove_alias(e.id, "Remo con barra")
        assert removed == 1
        # removing again -> 0
        assert repo.remove_alias(e.id, "Remo con barra") == 0

        with pytest.raises(ValueError):
            repo.add_alias(e.id, "   ")  # empty/whitespace

    def test_set_add_remove_tags(self, repo, session):
        """Replace, add, and remove tags ensuring idempotent behaviour."""
        e = ExerciseFactory(name="Squat", slug="squat")
        session.add(e)
        session.flush()

        # set exact set (creates tags)
        resulting = repo.set_tags_by_names(e.id, ["legs", "compound"])
        assert sorted([t.name for t in resulting]) == ["compound", "legs"]

        # add (union) one more
        resulting2 = repo.add_tags(e.id, ["strength"])
        assert sorted([t.name for t in resulting2]) == ["compound", "legs", "strength"]

        # remove a subset
        removed = repo.remove_tags(e.id, ["compound"])
        assert removed == 1
        names_now = [t.name for t in repo.list_tags(e.id)]
        assert sorted(names_now) == ["legs", "strength"]

        # set to empty → remove all
        resulting3 = repo.set_tags_by_names(e.id, [])
        assert resulting3 == []
        assert repo.list_tags(e.id) == []

    def test_list_by_tag(self, repo, session):
        """List exercises by tag and observe alphabetical ordering."""
        e1 = ExerciseFactory(name="Incline Bench", slug="incline-bench")
        e2 = ExerciseFactory(name="Push Up", slug="push-up")
        session.add_all([e1, e2])
        session.flush()

        repo.add_tags(e1.id, ["chest", "push"])
        repo.add_tags(e2.id, ["chest"])

        chest = repo.list_by_tag("chest", sort=["name"])
        assert [x.slug for x in chest] == ["incline-bench", "push-up"]
