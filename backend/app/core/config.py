# app/core/config.py
"""Application settings with environment-based config classes."""

from __future__ import annotations

import os
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
    """Base configuration shared across environments."""

    SECRET_KEY: str = "CHANGE_ME"  # default value
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./dev.db"  # default value
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False  # default value
    JSON_SORT_KEYS: bool = False
    PROPAGATE_EXCEPTIONS: bool = False  # centralized error handlers will format JSON
    LOG_LEVEL: str = "INFO"  # default value
    CORS_ORIGINS: str = "http://localhost:5173"  # default value

    # Flask built-ins that we keep explicit to avoid surprises
    DEBUG: bool = False
    TESTING: bool = False

    def __post_init__(self):
        # Dynamically set values from environment variables
        object.__setattr__(self, "SECRET_KEY", os.getenv("SECRET_KEY", self.SECRET_KEY))
        object.__setattr__(
            self,
            "SQLALCHEMY_DATABASE_URI",
            os.getenv("DATABASE_URL", self.SQLALCHEMY_DATABASE_URI),
        )
        object.__setattr__(
            self,
            "SQLALCHEMY_ECHO",
            _str2bool(os.getenv("SQLALCHEMY_ECHO", "false"), self.SQLALCHEMY_ECHO),
        )
        object.__setattr__(self, "LOG_LEVEL", os.getenv("LOG_LEVEL", self.LOG_LEVEL))
        object.__setattr__(self, "CORS_ORIGINS", os.getenv("CORS_ORIGINS", self.CORS_ORIGINS))


@dataclass(frozen=True)
class DevelopmentConfig(BaseConfig):
    """Development-friendly config."""

    DEBUG: bool = True  # default value
    SQLALCHEMY_ECHO: bool = False  # default value

    def __post_init__(self):
        # Dynamically set DEBUG and SQLALCHEMY_ECHO from environment if available
        object.__setattr__(
            self,
            "DEBUG",
            _str2bool(os.getenv("FLASK_DEBUG", "1"), self.DEBUG),
        )
        object.__setattr__(
            self,
            "SQLALCHEMY_ECHO",
            _str2bool(os.getenv("SQLALCHEMY_ECHO", "false"), self.SQLALCHEMY_ECHO),
        )


@dataclass(frozen=True)
class TestingConfig(BaseConfig):
    """Testing config: in-memory DB by default."""

    TESTING: bool = True
    DEBUG: bool = False  # keep error handlers active for JSON responses in tests
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"  # default value
    SQLALCHEMY_ECHO: bool = False
    PROPAGATE_EXCEPTIONS: bool = True  # helpful for pytest assertions

    def __post_init__(self):
        # Dynamically set SQLALCHEMY_DATABASE_URI from environment if available
        object.__setattr__(
            self,
            "SQLALCHEMY_DATABASE_URI",
            os.getenv("TEST_DATABASE_URL", self.SQLALCHEMY_DATABASE_URI),
        )


@dataclass(frozen=True)
class ProductionConfig(BaseConfig):
    """Production config."""

    DEBUG: bool = False
    SQLALCHEMY_ECHO: bool = False
    PROPAGATE_EXCEPTIONS: bool = False


def get_config() -> type[BaseConfig]:
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
