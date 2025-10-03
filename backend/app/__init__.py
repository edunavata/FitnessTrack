"""Expose the application factory at package level.

Provide convenient access to :func:`app.factory.create_app` so callers can
``from app import create_app`` without traversing the package structure.
"""

from __future__ import annotations

import sys as _sys

if __name__ != "app":
    _sys.modules.setdefault("app", _sys.modules[__name__])

from .factory import create_app

__all__ = ["create_app"]
