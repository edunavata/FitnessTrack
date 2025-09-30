"""Health and readiness endpoints for probes."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    """Report service liveness for container orchestrators.

    Returns
    -------
    dict
        JSON payload ``{"status": "ok"}`` with HTTP ``200``.

    Notes
    -----
    The handler performs no dependency checks and simply confirms the process
    is running.
    """
    return {"status": "ok"}


@bp.get("/readiness")
def readiness():
    """Expose readiness state used before receiving traffic.

    Returns
    -------
    dict
        JSON payload ``{"ready": True}`` with HTTP ``200``.

    Notes
    -----
    No downstream service checks are executed yet; expand this endpoint when
    readiness should cover database or cache availability.
    """
    return {"ready": True}
