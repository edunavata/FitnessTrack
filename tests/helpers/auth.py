"""Authentication helpers for tests."""

from __future__ import annotations

from datetime import timedelta

from flask_jwt_extended import create_access_token


def issue_token(identity: int, expires_delta: timedelta | None = None) -> str:
    """Generate a JWT for ``identity``.

    Parameters
    ----------
    identity:
        Subject identifier to encode in the token.
    expires_delta:
        Optional expiry delta. If ``None``, the default expiry is used.

    Returns
    -------
    str
        Encoded JWT string.
    """

    return create_access_token(identity=identity, expires_delta=expires_delta)


def expired_token(identity: int) -> str:
    """Return an already expired JWT for ``identity``.

    Parameters
    ----------
    identity:
        Subject identifier to encode in the token.

    Returns
    -------
    str
        Encoded JWT string that has already expired.
    """

    return create_access_token(identity=identity, expires_delta=timedelta(seconds=-1))

