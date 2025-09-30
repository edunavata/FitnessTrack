"""Health and readiness endpoints for uptime checks."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    """Report basic process health for liveness probes.

    Returns
    -------
    dict[str, str]
        Payload containing a static ``status`` field with value ``"ok"``.
    """
    return {"status": "ok"}


@bp.get("/readiness")
def readiness():
    """Indicate the service is ready to handle traffic.

    Returns
    -------
    dict[str, bool]
        Payload containing ``ready`` to signal readiness to orchestrators.

    Notes
    -----
    No downstream health checks are performed yet; the endpoint only reflects
    process-level readiness.
    """
    return {"ready": True}
