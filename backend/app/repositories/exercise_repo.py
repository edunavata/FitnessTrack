"""Repository utilities for the ``Exercise`` model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session


class ExerciseRepository:
    """Encapsulate exercise queries with placeholder responses."""

    def query(
        self,
        session: Session,
        filters: Mapping[str, object],
        *,
        page: int,
        limit: int,
        sort: Sequence[str],
    ) -> tuple[list[SimpleNamespace], int]:
        """Return an empty result set until real persistence is connected."""

        # TODO: Implement proper filtering and sorting using SQLAlchemy models.
        return [], 0

    def create(self, session: Session, data: Mapping[str, object]) -> SimpleNamespace:
        """Return a mock exercise record."""

        now = datetime.now(UTC)
        return SimpleNamespace(
            id=0,
            name=data.get("name"),
            slug=data.get("slug"),
            primary_muscle=data.get("primary_muscle"),
            movement=data.get("movement"),
            mechanics=data.get("mechanics"),
            force=data.get("force"),
            equipment=data.get("equipment"),
            difficulty=data.get("difficulty", "BEGINNER"),
            is_active=data.get("is_active", True),
            cues=data.get("cues"),
            instructions=data.get("instructions"),
            created_at=now,
            updated_at=now,
        )
