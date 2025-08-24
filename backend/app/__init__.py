"""Expose the application factory at package level."""

from __future__ import annotations

from .factory import create_app

__all__ = ["create_app"]
