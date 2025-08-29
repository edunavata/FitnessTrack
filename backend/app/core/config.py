"""Application settings with environment-based simple classes."""

from __future__ import annotations

import os

from dotenv import load_dotenv

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

    # Secretos / seguridad
    SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME")

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
    # Puedes activar echo desde env si lo necesitas
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)


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


def get_config() -> type[BaseConfig]:
    """Return the config class selected by environment variables.

    Priority:
      1) APP_ENV (production|development|testing)
      2) FLASK_ENV (legacy)
      3) default: DevelopmentConfig
    """
    env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
    if env in {"prod", "production"}:
        return ProductionConfig
    if env in {"test", "testing"}:
        return TestingConfig
    return DevelopmentConfig
