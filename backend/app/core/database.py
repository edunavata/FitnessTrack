"""SQLAlchemy database instance and migration setup."""
from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

# Global SQLAlchemy instance (initialized in factory)
db = SQLAlchemy()
