"""Repository utilities for the ``Exercise`` model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise


class ExerciseRepository:
    """Encapsulate frequently used ``Exercise`` queries."""

    sort_fields = {
        "created_at": Exercise.created_at,
        "updated_at": Exercise.updated_at,
        "name": Exercise.name,
        "slug": Exercise.slug,
    }

    def base_select(self) -> Select[Any]:
        """Return the base select for exercises."""

        return select(Exercise)

    def apply_filters(self, statement: Select[Any], filters: Mapping[str, Any]) -> Select[Any]:
        """Apply filter mapping to the select statement."""

        name = filters.get("name")
        if name:
            statement = statement.where(Exercise.name.ilike(f"%{name}%"))
        primary_muscle = filters.get("primary_muscle")
        if primary_muscle:
            statement = statement.where(Exercise.primary_muscle == primary_muscle)
        equipment = filters.get("equipment")
        if equipment:
            statement = statement.where(Exercise.equipment == equipment)
        is_active = filters.get("is_active")
        if is_active is not None:
            statement = statement.where(Exercise.is_active == bool(is_active))
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
    ) -> tuple[list[Exercise], int]:
        """Execute the select and return paginated exercise records."""

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
    ) -> tuple[list[Exercise], int]:
        """Return filtered and paginated exercises."""

        statement = self.apply_filters(self.base_select(), filters)
        statement = self.apply_sort(statement, sort)
        return self.paginate(session, statement, page=page, limit=limit)

    def create(self, session: Session, data: Mapping[str, Any]) -> Exercise:
        """Persist a new exercise entity."""

        exercise = Exercise(
            name=data["name"],
            slug=data["slug"],
            primary_muscle=data["primary_muscle"],
            movement=data["movement"],
            mechanics=data["mechanics"],
            force=data["force"],
            equipment=data["equipment"],
            difficulty=data.get("difficulty", "BEGINNER"),
            is_active=data.get("is_active", True),
            cues=data.get("cues"),
            instructions=data.get("instructions"),
        )
        session.add(exercise)
        return exercise
