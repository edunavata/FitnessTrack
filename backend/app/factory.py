"""Flask application factory."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

from app.api import register_blueprint_group
from app.core.config import get_config
from app.core.database import db
from app.core.errors import register_error_handlers
from app.core.logger import configure_logging

migrate = Migrate()
jwt = JWTManager()


def create_app() -> Flask:
    """Create and configure the Flask application.

    :returns: Configured Flask app instance.
    :rtype: Flask
    """
    Config = get_config()
    configure_logging(Config.LOG_LEVEL)
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)

    from app import models as _models  # noqa: F401

    migrate.init_app(app, db)
    jwt.init_app(app)

    # CORS (en varias líneas para evitar E501)
    origins = app.config.get("CORS_ORIGINS", "")
    allowed_origins = [o.strip() for o in origins.split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    _register_blueprints(app)

    # Centralized error handlers (JSON-only)
    register_error_handlers(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Register API blueprints by version."""
    api_base = app.config.get("API_BASE_PREFIX", "/api")
    # v1
    from app.api.v1 import API_VERSION as V1
    from app.api.v1 import REGISTRY as V1_REGISTRY

    register_blueprint_group(app, base_prefix=f"{api_base}/{V1}", entries=V1_REGISTRY)
