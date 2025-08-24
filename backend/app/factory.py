"""Flask application factory."""
from __future__ import annotations

import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate

from app.core.config import settings
from app.core.database import db
from app.core.logger import configure_logging


migrate = Migrate()


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns
    -------
    Flask
        Configured Flask application instance.
    """
    # Configure logging early
    configure_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=settings.SQLALCHEMY_DATABASE_URI,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        PROPAGATE_EXCEPTIONS=True,
    )

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": settings.CORS_ORIGINS.split(",")}})

    # Blueprints
    from app.api.v1.health import bp as health_bp
    app.register_blueprint(health_bp, url_prefix="/api/v1")

    # Root error handler
    @app.errorhandler(Exception)
    def on_error(err: Exception):
        """Catch-all error handler.

        Parameters
        ----------
        err:
            Unhandled exception.

        Returns
        -------
        tuple
            JSON error payload and HTTP status code.
        """
        logging.exception("Unhandled error")
        return jsonify({"error": "internal_server_error"}), 500

    return app
