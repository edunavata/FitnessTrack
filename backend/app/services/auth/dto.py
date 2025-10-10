# app/services/auth/dto.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

# ---------------------------- Input DTOs ---------------------------------- #


@dataclass(frozen=True, slots=True)
class LoginIn:
    """
    Input DTO for login.

    :param email: User email (normalized).
    :type email: str
    :param password: Raw password (to be verified).
    :type password: str
    """

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RefreshIn:
    """
    Input DTO for token refresh.

    :param refresh_token: Encoded refresh JWT.
    :type refresh_token: str
    """

    refresh_token: str


@dataclass(frozen=True, slots=True)
class LogoutIn:
    """
    Input DTO for logout.

    :param token: Encoded JWT (access or refresh).
    :type token: str
    :param all_sessions: If True, revoke all user sessions.
    :type all_sessions: bool
    """

    token: str
    all_sessions: bool = False


# --------------------------- Output DTOs ---------------------------------- #


@dataclass(frozen=True, slots=True)
class TokenPairOut:
    """
    Output DTO with access and refresh tokens.

    :param access_token: Encoded access JWT.
    :type access_token: str
    :param refresh_token: Encoded refresh JWT.
    :type refresh_token: str
    """

    access_token: str
    refresh_token: str


# ------------------------ Config DTO (optional) --------------------------- #


@dataclass(frozen=True, slots=True)
class AuthTokenConfig:
    """
    Token emission configuration.

    :param access_expires: Access token lifetime.
    :type access_expires: timedelta
    :param refresh_expires: Refresh token lifetime.
    :type refresh_expires: timedelta
    """

    access_expires: timedelta
    refresh_expires: timedelta
