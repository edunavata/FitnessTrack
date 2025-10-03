"""ETag helpers enabling optimistic concurrency for mutable resources."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from flask import Response


def generate_etag(entity: Any) -> str | None:
    """Generate a stable ETag value for a SQLAlchemy model instance.

    The helper concatenates the entity primary key and ``updated_at`` timestamp
    (when available) and hashes the string using SHA-256. When the entity lacks
    an ``id`` attribute the function returns ``None`` to indicate ETag support
    is not available.
    """

    identifier = getattr(entity, "id", None)
    if identifier is None:
        return None
    updated_at: datetime | None = getattr(entity, "updated_at", None)
    payload = f"{identifier}:{updated_at.isoformat() if updated_at else ''}".encode()
    return hashlib.sha256(payload).hexdigest()


def verify_etag(entity: Any, provided: str | None) -> bool:
    """Verify that a provided ETag matches the entity's current fingerprint."""

    if not provided:
        return False
    current = generate_etag(entity)
    return current == provided


def set_response_etag(response: Response, entity: Any) -> Response:
    """Attach an ``ETag`` header to a Flask response when possible."""

    value = generate_etag(entity)
    if value is not None:
        response.set_etag(value)
    return response
