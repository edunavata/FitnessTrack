"""Logging configuration utilities for the application factory."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with a stdout handler.

    Parameters
    ----------
    level: str, optional
        Logging level name such as ``"DEBUG"`` or ``"INFO"``. The value is
        uppercased before being applied.

    Notes
    -----
    Existing root handlers are cleared before installing the new handler to
    avoid duplicate log lines when the app factory is invoked multiple times.
    """
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S")
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
