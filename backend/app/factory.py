"""Application factory wiring Flask extensions and blueprints."""

from __future__ import annotations

from flask import Flask

from app.core.config import BaseConfig, get_config
from app.core.logger import configure_logging, init_app as init_logging


def create_app(
    config: str | type[BaseConfig] | object | None = None,
    *,
    instance_relative_config: bool = True,
    instance_config_filename: str = "config.py",
) -> Flask:
    """Build and configure the Flask application."""

    app = Flask(__name__, instance_relative_config=instance_relative_config)

    app.config.from_object(get_config() if config is None else config)
    if instance_relative_config and instance_config_filename:
        app.config.from_pyfile(instance_config_filename, silent=True)

    configure_logging(app.config.get("LOG_LEVEL", "INFO"))

    # Proxy headers if running behind a reverse proxy (optional module)
    from app.core import proxy

    proxy.init_app(app)

    from app.core import extensions

    extensions.init_app(app)

    init_logging(app)

    from app.core import cors

    cors.init_app(app)

    from app.api import init_app as init_api

    init_api(app)

    from app.core import errors

    errors.init_app(app)

    from app import cli as app_cli

    app_cli.init_app(app)

    return app
