from __future__ import annotations

from flask import Flask
from flask_cors import CORS


def init_app(app: Flask) -> None:
    """
    Configure CORS policy for /api/*.

    :param app: Flask application.
    :type app: Flask
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
