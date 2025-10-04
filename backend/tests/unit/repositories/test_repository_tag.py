"""Unit tests for ``TagRepository`` ensuring lookups and updates."""

from __future__ import annotations

import pytest
from app.repositories.tag import TagRepository


class TestTagRepository:
    """Confirm ``TagRepository`` ensures unique names and whitelisted updates."""
    @pytest.fixture()
    def repo(self) -> TagRepository:
        return TagRepository()

    def test_ensure_and_get_by_name(self, repo, session):
        """Ensure creates or fetches tags idempotently, and lookup returns it."""
        t1 = repo.ensure("mobility")
        assert t1.id is not None

        # idempotent
        t2 = repo.ensure("mobility")
        assert t2.id == t1.id

        got = repo.get_by_name("mobility")
        assert got is not None and got.id == t1.id

    def test_update_name_whitelist(self, repo, session):
        """Update a tag name using whitelisted fields and reject others."""
        t = repo.ensure("balance")
        # allowed update
        repo.update(t, name="balance-training")
        assert t.name == "balance-training"

        # invalid update field -> ValueError
        with pytest.raises(ValueError):
            repo.update(t, unknown="x")
