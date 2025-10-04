"""Service layer helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.extensions import db


def get_session(session: Session | None = None) -> Session:
    """Return the provided SQLAlchemy session or fall back to the global session."""

    return session or db.session


__all__ = ["get_session"]
