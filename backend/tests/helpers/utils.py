"""Tiny helpers used across tests."""

from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def not_raises(exception: type[BaseException]):
    """Assert that the wrapped block does not raise a given exception.

    Parameters
    ----------
    exception: type[BaseException]
        Exception type that must not occur within the context manager.

    Raises
    ------
    AssertionError
        If ``exception`` is raised by the wrapped block.
    """
    try:
        yield
    except exception as exc:  # pragma: no cover
        raise AssertionError(f"Did raise {exception}: {exc}") from exc
