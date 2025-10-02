"""Global Flask extension instances and initialization helpers."""

from __future__ import annotations

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
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
