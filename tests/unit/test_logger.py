"""Unit tests for the logging utility."""

from __future__ import annotations

import logging

from app.core.logger import configure_logging


def test_configure_logging_sets_level() -> None:
    """``configure_logging`` should set the root logger level."""

    # Act
    configure_logging("DEBUG")

    # Assert
    assert logging.getLogger().level == logging.DEBUG

