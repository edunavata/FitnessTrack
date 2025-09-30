"""Expose the shared SQLAlchemy instance used across the application.

The instance is initialized in :func:`app.factory.create_app` and reused for
model declarations, migrations, and CLI commands.
"""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

# Global SQLAlchemy instance (initialized in factory)
db = SQLAlchemy()
