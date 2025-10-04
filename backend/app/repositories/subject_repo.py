"""Repository utilities for the ``Subject`` model."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Mapping, Sequence
from uuid import uuid4

from sqlalchemy.orm import Session


class SubjectRepository:
    """Encapsulate subject queries with placeholder responses."""

    def query(
        self,
        session: Session,
        filters: Mapping[str, object],
        *,
        page: int,
        limit: int,
        sort: Sequence[str],
    ) -> tuple[list[SimpleNamespace], int]:
        """Return an empty result set until persistence is wired."""

        # TODO: Implement filtering and pagination against the Subject model.
        return [], 0

    def create(self, session: Session, data: Mapping[str, object]) -> SimpleNamespace:
        """Return a mock subject record."""

        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=0,
            user_id=data.get("user_id"),
            pseudonym=data.get("pseudonym") or uuid4(),
            created_at=now,
            updated_at=now,
        )
