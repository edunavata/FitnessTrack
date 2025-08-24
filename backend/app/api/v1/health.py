"""Health and readiness endpoints."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    """Liveness probe endpoint.

    Returns
    -------
    dict
        Simple status payload.
    """
    return {"status": "ok"}


@bp.get("/readiness")
def readiness():
    """Readiness probe endpoint.

    Returns
    -------
    dict
        Simple readiness payload (we can expand with DB checks later).
    """
    return {"ready": True}
