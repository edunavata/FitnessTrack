"""User model definition."""
from __future__ import annotations

from app.core.database import db


class User(db.Model):
    """Minimal user entity (we ampliaremos luego para auth JWT).

    Attributes
    ----------
    id:
        Primary key.
    email:
        Unique email address.
    created_at:
        Creation timestamp.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
