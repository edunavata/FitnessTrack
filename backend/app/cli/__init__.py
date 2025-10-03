"""Command-line interface registration for the Flask application."""

from __future__ import annotations

from flask import Flask

from .seed import seed_cli


def init_app(app: Flask) -> None:
    """Register application-specific CLI command groups.

    Parameters
    ----------
    app:
        Flask application instance whose CLI registry will receive the seed
        command group.
    """
    app.cli.add_command(seed_cli)
