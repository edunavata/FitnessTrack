"""Reusable SQLAlchemy mixins shared by domain models (typed 2.0)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

# Import db from your extensions module


class TimestampMixin:
    """Provide ``created_at`` and ``updated_at`` timestamp columns.

    Attributes
    ----------
    created_at:
        Timezone-aware timestamp filled by the database on insert.
    updated_at:
        Timezone-aware timestamp refreshed by the database on update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PKMixin:
    """Expose an integer surrogate primary key column named ``id``.

    Attributes
    ----------
    id:
        Auto-incrementing integer primary key managed by the database.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class ReprMixin:
    """Provide a concise ``__repr__`` including the class name and id."""

    def __repr__(self) -> str:
        """Return a short and useful string representation.

        :returns: Debug-friendly ``<ClassName id=...>``.
        :rtype: str
        """
        cls = self.__class__.__name__
        key = getattr(self, "id", None)
        return f"<{cls} id={key}>"
