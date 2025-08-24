# app/core/config.py
"""Application settings with environment-based config classes."""
from __future__ import annotations

import os
from typing import Type
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env if present (dev convenience)
load_dotenv()


def _str2bool(value: str, default: bool = False) -> bool:
    """Convert common truthy/falsey strings to bool."""
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class BaseConfig:
    """Base configuration shared across environments.

    Attributes
    ----------
    SECRET_KEY:
        Secret key for Flask (and later JWT).
    SQLALCHEMY_DATABASE_URI:
        SQLAlchemy connection string.
    SQLALCHEMY_TRACK_MODIFICATIONS:
        Disable costly tracking feature.
    SQLALCHEMY_ECHO:
        Echo SQL statements to logs.
    JSON_SORT_KEYS:
        Keep JSON order as defined.
    PROPAGATE_EXCEPTIONS:
        Let Flask handle exceptions via error handlers.
    LOG_LEVEL:
        Root logger level.
    CORS_ORIGINS:
        Comma-separated origins for CORS.
    """

    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME")
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = _str2bool(os.getenv("SQLALCHEMY_ECHO", "false"))
    JSON_SORT_KEYS: bool = False
    PROPAGATE_EXCEPTIONS: bool = False  # centralized error handlers will format JSON
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # Flask built-ins that we keep explicit to avoid surprises
    # Make sure Flask never returns HTML error pages in production
    DEBUG: bool = False
    TESTING: bool = False


@dataclass(frozen=True)
class DevelopmentConfig(BaseConfig):
    """Development-friendly config."""
    DEBUG: bool = _str2bool(os.getenv("FLASK_DEBUG", "1"), True)
    SQLALCHEMY_ECHO: bool = _str2bool(os.getenv("SQLALCHEMY_ECHO", "false"))


@dataclass(frozen=True)
class TestingConfig(BaseConfig):
    """Testing config: in-memory DB by default."""
    TESTING: bool = True
    DEBUG: bool = False  # keep error handlers active for JSON responses in tests
    SQLALCHEMY_DATABASE_URI: str = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ECHO: bool = False
    PROPAGATE_EXCEPTIONS: bool = True  # helpful for pytest assertions


@dataclass(frozen=True)
class ProductionConfig(BaseConfig):
    """Production config."""
    DEBUG: bool = False
    SQLALCHEMY_ECHO: bool = False
    PROPAGATE_EXCEPTIONS: bool = False


def get_config() -> Type[BaseConfig]:
    """Select the config class from environment.

    Priority order:
    1) APP_ENV (production|development|testing)
    2) FLASK_ENV (flask legacy var)
    3) default: DevelopmentConfig

    Returns
    -------
    Type[BaseConfig]
        The selected configuration class.
    """
    env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
    if env in {"prod", "production"}:
        return ProductionConfig
    if env in {"test", "testing"}:
        return TestingConfig
    return DevelopmentConfig
