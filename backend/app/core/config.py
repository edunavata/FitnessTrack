"""Application settings with environment-based simple classes."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Final

from dotenv import load_dotenv

# Public selector env var (keep neutral name to avoid collisions)
ENV_VAR: Final[str] = "APP_ENV"  # 'development' | 'testing' | 'production'


# Carga .env en desarrollo (no hace nada si no existe)
load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean flag from an environment variable.

    Parameters
    ----------
    name: str
        Environment variable to inspect.
    default: bool, optional
        Value returned when the variable is unset. Defaults to ``False``.

    Returns
    -------
    bool
        ``True`` if the value resembles ``{"1", "true", "yes", "y", "on"}``
        ignoring case; otherwise ``False`` or ``default`` when missing.
    """
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


class BaseConfig:
    """Base configuration shared across environments.

    Attributes
    ----------
    API_BASE_PREFIX: str
        Root path for registering API blueprints.
    SECRET_KEY: str
        Flask secret used for session signing. Defaults to a development-safe
        placeholder and should be overridden in production.
    JWT_SECRET_KEY: str
        Key used by ``flask-jwt-extended`` for signing access tokens.
    SQLALCHEMY_DATABASE_URI: str
        Database connection string consumed by SQLAlchemy.
    SQLALCHEMY_TRACK_MODIFICATIONS: bool
        Disabled to avoid extra overhead from the event system.
    SQLALCHEMY_ECHO: bool
        When ``True`` SQLAlchemy logs SQL statements for debugging.
    JSON_SORT_KEYS: bool
        Keeps JSON output order stable when ``False``.
    PROPAGATE_EXCEPTIONS: bool
        Controls Flask error propagation.
    LOG_LEVEL: str
        Root logging verbosity (``INFO`` by default).
    CORS_ORIGINS: str
        Comma-separated list of allowed origins for CORS.
    DEBUG: bool
        Toggles Flask debug mode.
    TESTING: bool
        Enables Flask testing mode when ``True``.

    Notes
    -----
    Values are primarily sourced from environment variables, enabling
    configuration without code changes.
    """

    API_BASE_PREFIX = "/api"

    # Secretos / seguridad
    SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_JWT")

    # DB
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)

    # Flask & JSON
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False

    # Logging & CORS
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # Built-ins de Flask
    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    """Configuration tailored for local development.

    Notes
    -----
    Enables debug mode by default and honors ``SQLALCHEMY_ECHO`` for verbose
    SQL logging when requested.
    """

    DEBUG = env_bool("FLASK_DEBUG", True)
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)
    CORS_MAX_AGE = 600  # 10 minutes


class TestingConfig(BaseConfig):
    """Configuration for automated test runs.

    Notes
    -----
    - Forces ``TESTING`` mode and disables debug logs.
    - Uses an in-memory SQLite database unless ``TEST_DATABASE_URL`` is set.
    - Propagates exceptions so pytest can surface tracebacks directly.
    """

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)
    PROPAGATE_EXCEPTIONS = True


class ProductionConfig(BaseConfig):
    """Configuration defaults for production deployments.

    Notes
    -----
    Keeps debug and SQL echoing disabled while relying on WSGI-level log
    configuration for noise control.
    """

    DEBUG = False
    SQLALCHEMY_ECHO = False
    PROPAGATE_EXCEPTIONS = False


# Map names -> classes (simple, explicit)
CONFIG_MAP: Mapping[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> type[BaseConfig]:
    """Return the configuration class inferred from ``APP_ENV``.

    Returns
    -------
    type[BaseConfig]
        Class to pass to :meth:`flask.Config.from_object`.

    Notes
    -----
    Falls back to :class:`DevelopmentConfig` when ``APP_ENV`` is unset or
    unknown.
    """
    name = os.getenv(ENV_VAR, "development").strip().lower()
    return CONFIG_MAP.get(name, DevelopmentConfig)
