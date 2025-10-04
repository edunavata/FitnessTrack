"""Repository utilities for the ``Routine`` model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.routine import Routine


class RoutineRepository:
    """Encapsulate data-access patterns for routines."""

    sort_fields = {
        "created_at": Routine.created_at,
        "updated_at": Routine.updated_at,
        "name": Routine.name,
    }

    def base_select(self) -> Select[Any]:
        """Return the base select for routines."""

        return select(Routine)

    def apply_filters(self, statement: Select[Any], filters: Mapping[str, Any]) -> Select[Any]:
        """Apply filter mapping to the select statement."""

        owner_subject_id = filters.get("owner_subject_id")
        if owner_subject_id is not None:
            statement = statement.where(Routine.owner_subject_id == owner_subject_id)
        is_public = filters.get("is_public")
        if is_public is not None:
            statement = statement.where(Routine.is_public == bool(is_public))
        name = filters.get("name")
        if name:
            statement = statement.where(Routine.name.ilike(f"%{name}%"))
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
    ) -> tuple[list[Routine], int]:
        """Execute the select and return paginated routines."""

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
    ) -> tuple[list[Routine], int]:
        """Return filtered and paginated routine rows."""

        statement = self.apply_filters(self.base_select(), filters)
        statement = self.apply_sort(statement, sort)
        return self.paginate(session, statement, page=page, limit=limit)

    def create(self, session: Session, data: Mapping[str, Any]) -> Routine:
        """Persist a new routine record."""

        routine = Routine(
            owner_subject_id=data["owner_subject_id"],
            name=data["name"],
            description=data.get("description"),
            is_public=data.get("is_public", False),
        )
        session.add(routine)
        return routine
