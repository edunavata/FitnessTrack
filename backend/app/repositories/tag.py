# backend/app/repositories/tag.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import Select, select
from sqlalchemy.orm import InstrumentedAttribute

from app.models.exercise import Tag  # adjust path if needed
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """
    Persistence-only repository for :class:`app.models.exercise.Tag`.
    """

    model = Tag

    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        """Return safe sort columns."""
        return {
            "id": self.model.id,
            "name": self.model.name,
            "created_at": self.model.created_at,
        }

    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        """Restrict equality filters."""
        return {
            "id": self.model.id,
            "name": self.model.name,
        }

    def _updatable_fields(self) -> set[str]:
        """Allow updating tag name."""
        return {"name"}

    # --------- helpers ---------
    def get_by_name(self, name: str) -> Tag | None:
        """Return tag by exact name."""
        stmt: Select[Any] = select(self.model).where(self.model.name == name)
        result = self.session.execute(stmt).scalars().first()
        return cast(Tag | None, result)

    def ensure(self, name: str) -> Tag:
        """Return tag if exists; create otherwise (idempotent)."""
        n = name.strip()
        if not n:
            raise ValueError("tag name cannot be empty.")
        found = self.get_by_name(n)
        if found:
            return found
        t = Tag(name=n)
        self.session.add(t)
        self.flush()
        return t
