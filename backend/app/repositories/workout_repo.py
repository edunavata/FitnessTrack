"""Repository utilities for the ``WorkoutSession`` model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session


class WorkoutRepository:
    """Encapsulate workout queries with placeholder responses."""

    def query(
        self,
        session: Session,
        filters: Mapping[str, object],
        *,
        page: int,
        limit: int,
        sort: Sequence[str],
    ) -> tuple[list[SimpleNamespace], int]:
        """Return an empty result set until persistence is implemented."""

        # TODO: Implement SQLAlchemy-backed filtering for workouts.
        return [], 0

    def create(self, session: Session, data: Mapping[str, object]) -> SimpleNamespace:
        """Return a mock workout session."""

        now = datetime.now(UTC)
        return SimpleNamespace(
            id=0,
            subject_id=data.get("subject_id"),
            workout_date=data.get("workout_date"),
            status=data.get("status", "PENDING"),
            routine_day_id=data.get("routine_day_id"),
            cycle_id=data.get("cycle_id"),
            location=data.get("location"),
            perceived_fatigue=data.get("perceived_fatigue"),
            bodyweight_kg=data.get("bodyweight_kg"),
            notes=data.get("notes"),
            created_at=now,
            updated_at=now,
        )
