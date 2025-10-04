"""Tag repository exposing persistence-focused helpers.

The :class:`TagRepository` extends :class:`~app.repositories.base.BaseRepository`
to manage :class:`app.models.exercise.Tag` records. It provides basic lookup and
ensuring helpers while deferring transaction management to services.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import Select, select
from sqlalchemy.orm import InstrumentedAttribute

from app.models.exercise import Tag  # adjust path if needed
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Persist :class:`Tag` rows and expose simple lookup helpers.

    Sorting and filtering rely on whitelists inherited from the base
    repository, ensuring deterministic pagination and safe query construction.
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
        """Return a tag by its unique name.

        :param name: Tag name to search for.
        :type name: str
        :returns: Matching tag or ``None`` when absent.
        :rtype: Tag | None
        """
        stmt: Select[Any] = select(self.model).where(self.model.name == name)
        result = self.session.execute(stmt).scalars().first()
        return cast(Tag | None, result)

    def ensure(self, name: str) -> Tag:
        """Return a tag if it exists; otherwise create it idempotently.

        :param name: Name to normalise and ensure.
        :type name: str
        :returns: Existing or newly created tag.
        :rtype: Tag
        :raises ValueError: If the provided name is empty after trimming.
        """
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
