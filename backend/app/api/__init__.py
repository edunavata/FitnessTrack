"""Versioned API registration helpers."""

from __future__ import annotations

from flask import Flask


def init_app(app: Flask) -> None:
    """Register the available API versions on the Flask application."""

    base_prefix = app.config.get("API_BASE_PREFIX", "/api").rstrip("/") or "/api"
    from app.api.v1 import bp_v1

    app.register_blueprint(bp_v1, url_prefix=f"{base_prefix}/v1")


__all__ = ["init_app"]
