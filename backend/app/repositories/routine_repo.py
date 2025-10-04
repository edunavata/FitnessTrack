"""Repository utilities for the ``Routine`` model."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Mapping, Sequence

from sqlalchemy.orm import Session


class RoutineRepository:
    """Encapsulate routine queries with placeholder responses."""

    def query(
        self,
        session: Session,
        filters: Mapping[str, object],
        *,
        page: int,
        limit: int,
        sort: Sequence[str],
    ) -> tuple[list[SimpleNamespace], int]:
        """Return an empty result set until persistence is connected."""

        # TODO: Implement SQLAlchemy-powered filtering and pagination.
        return [], 0

    def create(self, session: Session, data: Mapping[str, object]) -> SimpleNamespace:
        """Return a mock routine record."""

        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=0,
            owner_subject_id=data.get("owner_subject_id"),
            name=data.get("name"),
            description=data.get("description"),
            is_public=bool(data.get("is_public", False)),
            created_at=now,
            updated_at=now,
        )
