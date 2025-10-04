"""Repository utilities for the ``User`` model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Encapsulate common ``User`` queries."""

    sort_fields = {
        "created_at": User.created_at,
        "updated_at": User.updated_at,
        "username": User.username,
        "email": User.email,
    }

    def base_select(self) -> Select[Any]:
        """Return the base select for the ``users`` table."""

        return select(User)

    def apply_filters(self, statement: Select[Any], filters: Mapping[str, Any]) -> Select[Any]:
        """Apply filtering criteria based on provided mapping."""

        email = filters.get("email")
        if email:
            statement = statement.where(func.lower(User.email).like(f"%{email.lower()}%"))
        username = filters.get("username")
        if username:
            statement = statement.where(User.username.ilike(f"%{username}%"))
        return statement

    def apply_sort(self, statement: Select[Any], tokens: Sequence[str]) -> Select[Any]:
        """Apply client-supplied sort tokens to the statement."""

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
    ) -> tuple[list[User], int]:
        """Execute the select with pagination returning domain objects."""

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
    ) -> tuple[list[User], int]:
        """Return a paginated list of users matching filters."""

        statement = self.apply_filters(self.base_select(), filters)
        statement = self.apply_sort(statement, sort)
        return self.paginate(session, statement, page=page, limit=limit)

    def create(self, session: Session, data: Mapping[str, Any]) -> User:
        """Instantiate and persist a ``User`` instance."""

        user = User(
            email=data["email"],
            username=data["username"],
            full_name=data.get("full_name"),
        )
        password = data.get("password")
        if password:
            user.password = password  # type: ignore[assignment]
        session.add(user)
        return user

    def get_by_email(self, session: Session, email: str) -> User | None:
        """Return a user by normalized email if present."""

        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, session: Session, user_id: int) -> User | None:
        """Return a user by identifier."""

        stmt = select(User).where(User.id == user_id)
        return session.execute(stmt).scalar_one_or_none()
