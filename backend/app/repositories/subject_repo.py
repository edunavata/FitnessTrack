"""Repository utilities for the ``Subject`` model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.subject import Subject


class SubjectRepository:
    """Encapsulate database access patterns for subjects."""

    sort_fields = {
        "created_at": Subject.created_at,
        "updated_at": Subject.updated_at,
        "id": Subject.id,
    }

    def base_select(self) -> Select[Any]:
        """Return the base select for subjects."""

        return select(Subject)

    def apply_filters(self, statement: Select[Any], filters: Mapping[str, Any]) -> Select[Any]:
        """Apply filter mapping to the select statement."""

        user_id = filters.get("user_id")
        if user_id is not None:
            statement = statement.where(Subject.user_id == user_id)
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
    ) -> tuple[list[Subject], int]:
        """Execute the select and return paginated subjects."""

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
    ) -> tuple[list[Subject], int]:
        """Return filtered and paginated subjects."""

        statement = self.apply_filters(self.base_select(), filters)
        statement = self.apply_sort(statement, sort)
        return self.paginate(session, statement, page=page, limit=limit)

    def create(self, session: Session, data: Mapping[str, Any]) -> Subject:
        """Persist a new subject."""

        subject = Subject(user_id=data.get("user_id"))
        session.add(subject)
        return subject
