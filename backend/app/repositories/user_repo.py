"""Repository utilities for the ``User`` model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session


class UserRepository:
    """Encapsulate user queries with lightweight placeholders."""

    def query(
        self,
        session: Session,
        filters: Mapping[str, object],
        *,
        page: int,
        limit: int,
        sort: Sequence[str],
    ) -> tuple[list[SimpleNamespace], int]:
        """Return an empty result set until the database layer is wired."""

        # TODO: Replace with real SQLAlchemy queries using the ``User`` model.
        return [], 0

    def create(self, session: Session, data: Mapping[str, object]) -> SimpleNamespace:
        """Return a mock user instance based on the provided payload."""

        now = datetime.now(UTC)
        return SimpleNamespace(
            id=0,
            email=data.get("email"),
            username=data.get("username"),
            full_name=data.get("full_name"),
            created_at=now,
            updated_at=now,
        )

    def get_by_email(self, session: Session, email: str) -> SimpleNamespace | None:
        """Return ``None`` until database lookups are implemented."""

        # TODO: Implement lookup by email once persistence is available.
        return None

    def get_by_id(self, session: Session, user_id: int) -> SimpleNamespace | None:
        """Return ``None`` until identity lookups are implemented."""

        # TODO: Implement lookup by identifier.
        return None
