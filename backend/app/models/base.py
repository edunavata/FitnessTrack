from __future__ import annotations

from datetime import datetime

from app.core.extensions import db


class TimestampMixin:
    """Common timestamps mixin.

    :ivar created_at: Creation datetime in UTC.
    :ivar updated_at: Last update datetime in UTC.
    """

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PKMixin:
    """Primary key mixin.

    :ivar id: Surrogate integer primary key.
    """

    id = db.Column(db.Integer, primary_key=True)


class ReprMixin:
    """Human-friendly __repr__ mixin."""

    def __repr__(self) -> str:
        # Short and useful representation for debugging
        cls = self.__class__.__name__
        key = getattr(self, "id", None)
        return f"<{cls} id={key}>"
