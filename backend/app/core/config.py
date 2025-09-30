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
    """Parse bools from environment variables."""
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


class BaseConfig:
    """Base configuration shared across environments."""

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
    """Development-friendly config."""

    DEBUG = env_bool("FLASK_DEBUG", True)
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)
    CORS_MAX_AGE = 600  # 10 minutes


class TestingConfig(BaseConfig):
    """Testing config: in-memory DB by default."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)
    PROPAGATE_EXCEPTIONS = True


class ProductionConfig(BaseConfig):
    """Production config."""

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
    """Return the selected config class based on ``APP_ENV``.

    :returns: Configuration class to pass to ``app.config.from_object``.
    :rtype: Type[BaseConfig]
    """
    name = os.getenv(ENV_VAR, "development").strip().lower()
    return CONFIG_MAP.get(name, DevelopmentConfig)
