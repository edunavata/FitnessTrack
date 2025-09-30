"""Tiny helpers used across tests."""

from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def not_raises(exception: type[BaseException]):
    """Context manager asserting that an exception is *not* raised.

    Parameters
    ----------
    exception:
        Exception type that should not be raised.
    """
    try:
        yield
    except exception as exc:  # pragma: no cover
        raise AssertionError(f"Did raise {exception}: {exc}") from exc
