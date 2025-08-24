"""Application settings and environment handling."""
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env if present (development convenience)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Strongly-typed settings loaded from environment.

    :raises ValueError: If required settings are missing.

    Attributes
    ----------
    ENV:
        Environment name (development|production|test).
    SECRET_KEY:
        Secret used by Flask and (más adelante) para firmar tokens.
    SQLALCHEMY_DATABASE_URI:
        Database URL. Falls back to local SQLite if not set.
    SQLALCHEMY_ECHO:
        Whether to echo SQL statements to logs.
    LOG_LEVEL:
        Root logger level.
    CORS_ORIGINS:
        Comma-separated origins allowed for CORS.
    """

    ENV: str = os.getenv("ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME")
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", "sqlite:///./dev.db"
    )
    SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")


settings = Settings()
