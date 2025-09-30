"""Reusable SQLAlchemy mixins shared by domain models."""

from __future__ import annotations

from datetime import datetime

from app.core.extensions import db


class TimestampMixin:
    """Provide ``created_at`` and ``updated_at`` timestamp columns.

    Attributes
    ----------
    created_at: sqlalchemy.sql.schema.Column
        UTC timestamp filled on insert.
    updated_at: sqlalchemy.sql.schema.Column
        UTC timestamp refreshed on updates via SQLAlchemy ``onupdate``.
    """

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PKMixin:
    """Expose an integer surrogate primary key column named ``id``.

    Attributes
    ----------
    id: sqlalchemy.sql.schema.Column
        Auto-incrementing integer primary key managed by the database.
    """

    id = db.Column(db.Integer, primary_key=True)


class ReprMixin:
    """Provide a concise ``__repr__`` including the class name and id."""

    def __repr__(self) -> str:
        # Short and useful representation for debugging
        cls = self.__class__.__name__
        key = getattr(self, "id", None)
        return f"<{cls} id={key}>"
