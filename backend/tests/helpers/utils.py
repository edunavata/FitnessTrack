"""Tiny helpers shared across test modules."""

from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def not_raises(exception: type[BaseException]):
    """Context manager asserting that an exception is *not* raised.

    Parameters
    ----------
    exception: type[BaseException]
        Exception type that should not be raised within the context.

    Yields
    ------
    None
        Control enters the managed block when the exception is absent.
    """
    try:
        yield
    except exception as exc:  # pragma: no cover
        raise AssertionError(f"Did raise {exception}: {exc}") from exc
