from __future__ import annotations

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Global singletons (import-safe)
db: SQLAlchemy = SQLAlchemy(session_options={"autoflush": False})
migrate = Migrate()
jwt = JWTManager()


def init_app(app: Flask) -> None:
    """
    Initialize Flask extensions.

    :param app: Flask application.
    :type app: Flask
    """
    db.init_app(app)

    # Ensure models are imported so Alembic sees metadata
    from app import models as _models  # noqa: F401

    migrate.init_app(app, db)
    jwt.init_app(app)
