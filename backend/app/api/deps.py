"""Shared API helpers for request parsing and cross-cutting concerns."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from flask import Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import Forbidden
from app.core.extensions import db
from app.schemas.common import PaginationQuerySchema

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(slots=True)
class Pagination:
    """Container holding pagination arguments parsed from the request."""

    page: int
    limit: int
    sort: list[str]


def parse_pagination(default_limit: int = 20, max_limit: int = 200) -> Pagination:
    """Parse pagination parameters from ``request.args`` using Marshmallow."""

    schema = PaginationQuerySchema(default_limit=default_limit, max_limit=max_limit)
    data = schema.load(request.args)
    return Pagination(page=data["page"], limit=data["limit"], sort=data["sort"])


def apply_sorting(
    statement: Select[Any],
    sort_fields: Mapping[str, Any],
    tokens: Iterable[str],
) -> Select[Any]:
    """Apply ordering clauses to a SQLAlchemy ``Select`` statement."""

    order_clauses: list[Any] = []
    for raw in tokens:
        direction = raw.startswith("-")
        key = raw[1:] if direction else raw
        column = sort_fields.get(key)
        if column is None:
            continue
        order_clauses.append(column.desc() if direction else column.asc())
    if order_clauses:
        statement = statement.order_by(*order_clauses)
    return statement


def paginate_query(
    session: Session,
    statement: Select[Any],
    pagination: Pagination,
) -> tuple[list[Any], int]:
    """Execute the select with pagination returning items and total count."""

    page = max(pagination.page, 1)
    limit = max(pagination.limit, 1)
    count_stmt = select(func.count()).select_from(statement.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one_or_none() or 0
    offset = (page - 1) * limit
    paginated = statement.limit(limit).offset(offset)
    items = list(session.execute(paginated).scalars())
    return items, int(total)


def get_session() -> Session:
    """Return the SQLAlchemy session bound to the current application."""

    return db.session


def require_auth(func: F) -> F:
    """Ensure the request carries a valid JWT access token."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        verify_jwt_in_request(optional=False)
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def require_scope(required: str) -> Callable[[F], F]:
    """Ensure the verified JWT contains the requested scope claim."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            verify_jwt_in_request(optional=False)
            claims = get_jwt() or {}
            scopes = set(claims.get("scopes", []))
            if required not in scopes:
                raise Forbidden("Insufficient scope")
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def idempotency_cache() -> dict[str, Any]:
    """Return the process-local idempotency cache."""

    default: dict[str, Any] = {}
    store = current_app.extensions.setdefault("idempotency_cache", default)
    return cast(dict[str, Any], store)


def enforce_idempotency(key: str | None) -> tuple[bool, dict[str, Any] | None]:
    """Check whether the provided ``Idempotency-Key`` was already used."""

    if not key:
        return False, None
    cache = idempotency_cache()
    cached = cache.get(key)
    if cached is None:
        return False, None
    return True, cached


def store_idempotent_response(key: str | None, payload: dict[str, Any]) -> None:
    """Persist the response blueprint for subsequent replays."""

    if not key:
        return
    cache = idempotency_cache()
    cache[key] = payload
    # TODO: Replace the in-memory dictionary with Redis or another shared backend.


def build_cached_response(payload: dict[str, Any]) -> Response:
    """Rehydrate a Flask response object from cached payload metadata."""

    response = json_response(payload.get("body", {}), status=payload.get("status", 200))
    for header, value in payload.get("headers", {}).items():
        response.headers[header] = value
    return response


def json_response(payload: Any, *, status: int = 200) -> Response:
    """Return a JSON response enforcing a consistent MIME type."""

    response = jsonify(payload)
    response.status_code = status
    return response


def timing(func: F) -> F:
    """Decorator capturing handler execution time in milliseconds."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            request_endpoint = getattr(request, "endpoint", None)
            current_app.logger.debug(
                "request.elapsed",
                extra={"endpoint": request_endpoint, "elapsed_ms": round(elapsed_ms, 2)},
            )

    return wrapper  # type: ignore[return-value]
