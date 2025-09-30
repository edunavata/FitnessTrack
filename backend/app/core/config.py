"""Application settings grouped by environment-friendly classes."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Final

from dotenv import load_dotenv

# Public selector env var (keep neutral name to avoid collisions)
ENV_VAR: Final[str] = "APP_ENV"  # 'development' | 'testing' | 'production'


# Load a ``.env`` file locally; this is a no-op when absent in production.
load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean values from environment variables.

    Parameters
    ----------
    name: str
        Name of the environment variable to inspect.
    default: bool
        Fallback returned when the variable is undefined.

    Returns
    -------
    bool
        ``True`` when the environment value matches typical truthy strings.
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
        Root path for the public API routes.
    SECRET_KEY: str
        Flask secret key used for session signing.
    JWT_SECRET_KEY: str
        Secret used by :mod:`flask_jwt_extended` for token signing.
    SQLALCHEMY_DATABASE_URI: str
        Database connection string consumed by SQLAlchemy.
    SQLALCHEMY_ECHO: bool
        Emits SQL statements when ``True`` for easier debugging.
    LOG_LEVEL: str
        Root logging level consumed by :func:`configure_logging`.
    CORS_ORIGINS: str
        Comma-separated list of origins allowed to access the API.
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
    """Development-friendly configuration with verbose defaults."""

    DEBUG = env_bool("FLASK_DEBUG", True)
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)
    CORS_MAX_AGE = 600  # 10 minutes


class TestingConfig(BaseConfig):
    """Testing configuration using an in-memory SQLite database."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)
    PROPAGATE_EXCEPTIONS = True


class ProductionConfig(BaseConfig):
    """Production configuration with conservative logging and safety flags."""

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
    """Return the configuration class selected via ``APP_ENV``.

    Returns
    -------
    type[BaseConfig]
        Config class consumed by :meth:`Flask.from_object`.

    Notes
    -----
    Defaults to :class:`DevelopmentConfig` when ``APP_ENV`` is unset or holds
    an unknown value.
    """
    name = os.getenv(ENV_VAR, "development").strip().lower()
    return CONFIG_MAP.get(name, DevelopmentConfig)
