"""Expose :func:`app.factory.create_app` at package import time.

Importing :mod:`app` makes the ``create_app`` factory readily available for
Flask's CLI and WSGI servers without touching the internal package layout.
"""

from __future__ import annotations

from .factory import create_app

__all__ = ["create_app"]
