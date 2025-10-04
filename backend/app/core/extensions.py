"""Global Flask extension instances and initialization helpers."""

from __future__ import annotations

from flask import Flask
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

try:  # Optional OpenAPI support
    from flask_smorest import Api
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Api = None
    api = None
else:  # pragma: no cover - simple wiring
    api = Api()

convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)

db: SQLAlchemy = SQLAlchemy(session_options={"autoflush": False}, metadata=metadata)
migrate = Migrate(render_as_batch=True)
jwt = JWTManager()
cache = Cache()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def init_app(app: Flask) -> None:
    """Initialize extensions on the provided Flask application."""

    db.init_app(app)
    from app import models  # noqa: F401 - ensure model registration

    migrate.init_app(app, db)
    jwt.init_app(app)

    cache_config = {
        "CACHE_TYPE": app.config.get("CACHE_TYPE", "SimpleCache"),
        "CACHE_DEFAULT_TIMEOUT": app.config.get("CACHE_DEFAULT_TIMEOUT", 300),
    }
    cache.init_app(app, config=cache_config)

    limiter.init_app(app)
    limiter.default_limits = app.config.get("RATELIMIT_DEFAULT", [])

    if api is not None:
        api.init_app(app)
    else:
        app.logger.debug("Flask-Smorest not installed; OpenAPI generation disabled.")


__all__ = ["db", "migrate", "jwt", "cache", "limiter", "api", "init_app"]
