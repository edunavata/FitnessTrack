"""Repository utilities for the ``WorkoutSession`` model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.workout import WorkoutSession


class WorkoutRepository:
    """Encapsulate database access for workout sessions."""

    sort_fields = {
        "workout_date": WorkoutSession.workout_date,
        "created_at": WorkoutSession.created_at,
        "updated_at": WorkoutSession.updated_at,
    }

    def base_select(self) -> Select[Any]:
        """Return the base select for workout sessions."""

        return select(WorkoutSession)

    def apply_filters(self, statement: Select[Any], filters: Mapping[str, Any]) -> Select[Any]:
        """Apply filter mapping to the select statement."""

        subject_id = filters.get("subject_id")
        if subject_id is not None:
            statement = statement.where(WorkoutSession.subject_id == subject_id)
        status = filters.get("status")
        if status:
            statement = statement.where(WorkoutSession.status == status)
        date_from = filters.get("date_from")
        if date_from is not None:
            statement = statement.where(WorkoutSession.workout_date >= date_from)
        date_to = filters.get("date_to")
        if date_to is not None:
            statement = statement.where(WorkoutSession.workout_date <= date_to)
        return statement

    def apply_sort(self, statement: Select[Any], tokens: Sequence[str]) -> Select[Any]:
        """Apply sorting instructions to the statement."""

        orders: list[Any] = []
        for token in tokens:
            desc = token.startswith("-")
            key = token[1:] if desc else token
            column = self.sort_fields.get(key)
            if column is None:
                continue
            orders.append(column.desc() if desc else column.asc())
        if orders:
            statement = statement.order_by(*orders)
        return statement

    def paginate(
        self, session: Session, statement: Select[Any], *, page: int, limit: int
    ) -> tuple[list[WorkoutSession], int]:
        """Execute the select and return paginated workouts."""

        page = max(page, 1)
        limit = max(limit, 1)
        count_stmt = select(func.count()).select_from(statement.order_by(None).subquery())
        total = session.execute(count_stmt).scalar_one_or_none() or 0
        offset = (page - 1) * limit
        result = session.execute(statement.limit(limit).offset(offset))
        return list(result.scalars()), int(total)

    def query(
        self,
        session: Session,
        filters: Mapping[str, Any],
        *,
        page: int,
        limit: int,
        sort: Sequence[str],
    ) -> tuple[list[WorkoutSession], int]:
        """Return filtered and paginated workout sessions."""

        statement = self.apply_filters(self.base_select(), filters)
        statement = self.apply_sort(statement, sort)
        return self.paginate(session, statement, page=page, limit=limit)

    def create(self, session: Session, data: Mapping[str, Any]) -> WorkoutSession:
        """Persist a new workout session."""

        workout = WorkoutSession(
            subject_id=data["subject_id"],
            workout_date=data["workout_date"],
            status=data.get("status", "PENDING"),
            routine_day_id=data.get("routine_day_id"),
            cycle_id=data.get("cycle_id"),
            location=data.get("location"),
            perceived_fatigue=data.get("perceived_fatigue"),
            bodyweight_kg=data.get("bodyweight_kg"),
            notes=data.get("notes"),
        )
        session.add(workout)
        return workout
