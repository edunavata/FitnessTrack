"""Health endpoints for Kubernetes-style probes."""

from __future__ import annotations

import time
from http import HTTPStatus

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.extensions import db

from ..deps import json_response, timing
from . import api_v1


@api_v1.get("/health")
@timing
def health() -> tuple[dict[str, object], int]:
    """Return service and database status information.

    The handler executes ``SELECT 1`` to validate the database connection and
    returns a JSON payload compatible with uptime monitors.

    :returns: Tuple containing the payload dictionary and HTTP status code.
    :rtype: tuple[dict[str, object], int]
    """

    # Measure timing to surface latency in the payload.
    started = time.perf_counter()
    db_status = "up"
    try:
        # Issue a lightweight query to ensure the primary database is reachable.
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:  # pragma: no cover - exercised in production outages
        current_app.logger.exception("Health DB check failed", exc_info=exc)
        db_status = "down"
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    status_code = HTTPStatus.OK if db_status == "up" else HTTPStatus.SERVICE_UNAVAILABLE
    payload = {
        "status": "ok" if status_code == HTTPStatus.OK else "degraded",
        "db": {"status": db_status},
        "latency_ms": latency_ms,
    }
    return payload, status_code.value
