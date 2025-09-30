"""CORS configuration helper for API resources."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS


def init_app(app: Flask) -> None:
    """Configure CORS for API endpoints based on application config.

    Parameters
    ----------
    app: flask.Flask
        Application whose ``CORS_ORIGINS`` and ``CORS_MAX_AGE`` settings are
        consulted. When ``CORS_ORIGINS`` is blank or ``"*"`` the policy allows
        any origin but disables credential support.
    """
    raw_origins = app.config.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    wildcard = len(origins) == 0 or origins == ["*"]

    CORS(
        app,
        resources={r"/api/*": {"origins": "*" if wildcard else origins}},
        supports_credentials=not wildcard,
        max_age=app.config.get("CORS_MAX_AGE", 600),
    )
