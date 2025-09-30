"""Application factory wiring Flask extensions and blueprints."""

from __future__ import annotations

from flask import Flask

from app.core.config import BaseConfig, get_config
from app.core.logger import configure_logging


def create_app(
    config: str | type[BaseConfig] | object | None = None,
    *,
    instance_relative_config: bool = True,
    instance_config_filename: str = "config.py",
) -> Flask:
    """Build and configure the Flask application.

    Parameters
    ----------
    config: str | type[BaseConfig] | object | None, optional
        Explicit configuration object or import string. ``None`` selects the
        configuration from :func:`app.core.config.get_config` using
        ``APP_ENV``.
    instance_relative_config: bool, optional
        Whether to resolve instance configuration files relative to
        ``instance_path``. Defaults to ``True`` to support per-deployment
        overrides.
    instance_config_filename: str, optional
        Name of the optional instance configuration file loaded via
        :meth:`flask.Config.from_pyfile`.

    Returns
    -------
    flask.Flask
        Fully initialized application with extensions, CORS, proxies, API, and
        error handlers registered.

    Notes
    -----
    - Logging is configured eagerly so early failures are captured.
    - The application will attempt to load ``instance_config_filename`` even
      when ``config`` is provided unless ``instance_relative_config`` is
      ``False``.
    """
    app = Flask(__name__, instance_relative_config=instance_relative_config)

    # Config
    app.config.from_object(get_config() if config is None else config)
    if instance_relative_config and instance_config_filename:
        app.config.from_pyfile(instance_config_filename, silent=True)

    # Logging ASAP
    configure_logging(app.config.get("LOG_LEVEL", "INFO"))

    # Proxy (opcional si externalizas)
    from app.core import proxy

    proxy.init_app(app)

    # Extensiones
    from app.core import extensions

    extensions.init_app(app)

    # CORS
    from app.core import cors

    cors.init_app(app)

    # API
    from app import api

    api.init_app(app)

    # Errores
    from app.core import errors

    errors.init_app(app)

    # Shell/CLI
    # from app.core import cli
    # cli.init_app(app)

    return app
