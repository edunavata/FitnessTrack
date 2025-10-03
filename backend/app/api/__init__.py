"""API blueprint wiring and helper registration."""

from __future__ import annotations

from flask import Flask

from .errors import register_problem_handlers
from .v1 import api_v1

__all__ = ["init_app", "api_v1"]


def init_app(app: Flask) -> None:
    """Attach versioned API blueprints to the Flask application.

    Parameters
    ----------
    app:
        Flask application created via :func:`app.factory.create_app`.

    Notes
    -----
    - The API is versioned under ``/api/v1`` following a URI-based strategy.
    - RFC 7807 problem handlers are registered on the blueprint before the
      blueprint is attached to the app to guarantee consistent error payloads.
    - Future versions can be registered by extending this module without
      changing the application factory signature.
    """

    if not getattr(api_v1, "_problem_handlers_registered", False):
        register_problem_handlers(api_v1)
        setattr(api_v1, "_problem_handlers_registered", True)
    app.register_blueprint(api_v1)
