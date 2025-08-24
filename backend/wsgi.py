"""WSGI entrypoint to run the Flask app."""

from __future__ import annotations

from app import create_app

app = create_app()
