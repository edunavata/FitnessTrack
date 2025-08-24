# app/factory.py
"""Flask application factory."""
from __future__ import annotations

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from app.core.config import get_config
from app.core.database import db
from app.core.errors import register_error_handlers
from app.core.logger import configure_logging

migrate = Migrate()


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns
    -------
    Flask
        Configured Flask app instance.
    """
    Config = get_config()

    # Configure logging early (based on config)
    configure_logging(Config.LOG_LEVEL)

    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # CORS
    origins = app.config.get("CORS_ORIGINS", "")
    CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in origins.split(",") if o.strip()]}})

    # Blueprints
    from app.api.v1.health import bp as health_bp
    app.register_blueprint(health_bp, url_prefix="/api/v1")

    # Centralized error handlers (JSON-only)
    register_error_handlers(app)

    return app
