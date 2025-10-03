"""Version 1 of the public REST API."""

from __future__ import annotations

from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")
"""Primary blueprint hosting the v1 REST surface."""


def _register_modules() -> None:
    """Import resource modules so route declarations are executed."""

    from . import cycles  # noqa: F401
    from . import exercises  # noqa: F401
    from . import health  # noqa: F401
    from . import routines  # noqa: F401
    from . import subjects  # noqa: F401
    from . import users  # noqa: F401
    from . import workouts  # noqa: F401


_register_modules()

__all__ = ["api_v1"]
