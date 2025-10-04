"""Health check endpoint."""

from __future__ import annotations

from flask import Blueprint, current_app
from sqlalchemy import text

from app.api.deps import json_response, timing
from app.core.extensions import db

bp = Blueprint("health", __name__)


@bp.get("/health")
@timing
def healthcheck():
    """Return application and database health information."""

    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - depends on DB backend
        current_app.logger.exception("healthcheck.db_error")
        db_status = "fail"
    version = current_app.config.get("APP_VERSION", "dev")
    commit = current_app.config.get("APP_COMMIT", "unknown")
    payload = {"status": "ok", "db": db_status, "version": version, "commit": commit}
    return json_response(payload)
