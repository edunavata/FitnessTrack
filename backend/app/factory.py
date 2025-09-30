# app/factory.py
from __future__ import annotations

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix

from app.api import register_blueprint_group
from app.core.config import get_config
from app.core.database import db
from app.core.errors import register_error_handlers
from app.core.logger import configure_logging

# Globally created extension instances (singletons)
migrate = Migrate()
jwt = JWTManager()


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    :returns: Configured Flask application.
    :rtype: Flask
    """
    # Load config and configure logging as early as possible
    Config = get_config()
    configure_logging(Config.LOG_LEVEL)

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    _configure_proxies(app)
    _init_extensions(app)
    _configure_cors(app)
    _register_blueprints(app)
    register_error_handlers(app)
    _register_shellcontext(app)
    _register_cli(app)

    return app


# ---------- internals ----------


def _configure_proxies(app: Flask) -> None:
    """
    Attach ProxyFix when running behind a reverse proxy.

    This preserves ``remote_addr``, scheme and host when proxied.

    :param app: Flask application instance.
    :rtype: None
    """
    if app.config.get("USE_PROXYFIX", True):
        # Conservative defaults; tune if your proxy chain differs.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


def _init_extensions(app: Flask) -> None:
    """
    Initialize Flask extensions (DB, migrations, JWT).

    :param app: Flask application instance.
    :rtype: None
    """
    db.init_app(app)

    # Import models for Alembic autogenerate to see metadata (side effect only).
    from app import models as _models  # noqa: F401

    migrate.init_app(app, db)
    jwt.init_app(app)


def _configure_cors(app: Flask) -> None:
    """
    Configure CORS for the API surface.

    - Reads comma-separated origins from ``CORS_ORIGINS`` config key.
    - Enables credentials only when origins are explicit (no wildcard).

    :param app: Flask application instance.
    :rtype: None
    """
    raw_origins = app.config.get("CORS_ORIGINS", "")
    origins: list[str] = [o.strip() for o in raw_origins.split(",") if o.strip()]
    wildcard = len(origins) == 0 or origins == ["*"]

    cors_kwargs: dict = {
        "resources": {r"/api/*": {"origins": "*" if wildcard else origins}},
        # Only allow credentials if no wildcard to avoid browser rejections
        "supports_credentials": not wildcard,
        "max_age": app.config.get("CORS_MAX_AGE", 600),
    }
    CORS(app, **cors_kwargs)


def _register_blueprints(app: Flask) -> None:
    """
    Register versioned API blueprints.

    :param app: Flask application instance.
    :rtype: None
    """
    api_base = app.config.get("API_BASE_PREFIX", "/api")

    # v1 registry
    from app.api.v1 import API_VERSION as V1
    from app.api.v1 import REGISTRY as V1_REGISTRY

    register_blueprint_group(app, base_prefix=f"{api_base}/{V1}", entries=V1_REGISTRY)

    # Future versions:
    # from app.api.v2 import API_VERSION as V2, REGISTRY as V2_REGISTRY
    # register_blueprint_group(app, base_prefix=f"{api_base}/{V2}", entries=V2_REGISTRY)


def _register_shellcontext(app: Flask) -> None:
    """
    Add helpful objects to ``flask shell``.

    :param app: Flask application instance.
    :rtype: None
    """

    @app.shell_context_processor
    def _ctx() -> dict[str, object]:
        """
        Provide default shell context.

        :returns: Mapping of names to objects for interactive shell.
        :rtype: dict[str, object]
        """
        return {"db": db}


def _register_cli(app: Flask) -> None:
    """
    Register custom CLI commands (placeholder).

    :param app: Flask application instance.
    :rtype: None
    """
    # Example:
    # @app.cli.command("seed")
    # def seed() -> None:
    #     """Seed database with initial data."""
    #     ...
    pass
