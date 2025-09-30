from __future__ import annotations

from datetime import datetime

from app.core.database import db


class TimestampMixin:
    """Add ``created_at`` and ``updated_at`` timestamp columns to models.

    Attributes
    ----------
    created_at
        Creation timestamp stored in UTC.
    updated_at
        Timestamp automatically refreshed on updates.
    """

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PKMixin:
    """Provide a surrogate integer primary key column named ``id``.

    Attributes
    ----------
    id
        Auto-incrementing primary key for SQLAlchemy models.
    """

    id = db.Column(db.Integer, primary_key=True)


class ReprMixin:
    """Provide a concise ``__repr__`` for debugging models."""

    def __repr__(self) -> str:
        # Short and useful representation for debugging
        cls = self.__class__.__name__
        key = getattr(self, "id", None)
        return f"<{cls} id={key}>"
