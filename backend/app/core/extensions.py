"""Global Flask extension instances and initialization helpers."""

from __future__ import annotations

import redis  # type: ignore[import-untyped]
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from redis.exceptions import RedisError  # type: ignore[import-untyped]
from sqlalchemy import MetaData

# Global naming convention for all constraints
# Tokens útiles:
#   %(table_name)s, %(column_0_name)s, %(referred_table_name)s, %(referred_table_name)s, etc.
#   Para compuestas: usa _col_%(column_0_name)s_%(column_1_name)s... si quieres, o un hash.
convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)

# Global singletons (import-safe)
db: SQLAlchemy = SQLAlchemy(session_options={"autoflush": False}, metadata=metadata)
migrate = Migrate(render_as_batch=True)
jwt = JWTManager()
redis_client: redis.Redis | None = None


def init_app(app: Flask) -> None:
    """Initialize SQLAlchemy, migrations, and JWT extensions.

    Parameters
    ----------
    app: flask.Flask
        Application used to bind extension instances. This call imports the
        :mod:`app.models` package to ensure SQLAlchemy metadata is ready for
        migrations.
    """
    db.init_app(app)

    # Ensure models are imported so Alembic sees metadata
    from app import models as _models  # noqa: F401

    migrate.init_app(app, db)
    jwt.init_app(app)

    global redis_client
    redis_url = app.config.get("REDIS_URL")
    if not redis_url:
        redis_client = None
        app.extensions.pop("redis_client", None)
        return

    redis_client = redis.Redis.from_url(redis_url)
    try:
        redis_client.ping()
    except RedisError as exc:
        raise RuntimeError(f"Failed to connect to Redis at {redis_url!r}") from exc
    app.extensions["redis_client"] = redis_client


def get_redis() -> redis.Redis:
    """Return the initialized Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized. Call init_app() first.")
    return redis_client
