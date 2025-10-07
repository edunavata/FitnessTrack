"""
DTOs for IdentityService.

Data Transfer Objects (DTOs) isolate the service layer from ORM models,
ensuring clear input/output contracts and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Input DTOs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class UserRegisterIn:
    """
    Input DTO for user registration.

    :param email: Login email (normalized to lowercase).
    :type email: str
    :param password: Raw password to be hashed by the model.
    :type password: str
    :param username: Public username.
    :type username: str
    :param full_name: Optional real name.
    :type full_name: str | None
    """

    email: str
    password: str
    username: str
    full_name: str | None = None


@dataclass(frozen=True, slots=True)
class UserAuthIn:
    """
    Input DTO for authentication.

    :param email: Login email.
    :type email: str
    :param password: Raw password.
    :type password: str
    """

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class UserUpdateIn:
    """
    Input DTO for updating user PII fields.

    :param email: Optional new email.
    :type email: str | None
    :param username: Optional new username.
    :type username: str | None
    :param full_name: Optional new full name.
    :type full_name: str | None
    :param if_match: Optional ETag for optimistic concurrency.
    :type if_match: str | None
    """

    email: str | None = None
    username: str | None = None
    full_name: str | None = None
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class UserPasswordChangeIn:
    """
    Input DTO for changing a user's password.

    :param user_id: User identifier.
    :type user_id: int
    :param old_password: Current password.
    :type old_password: str
    :param new_password: New password (raw).
    :type new_password: str
    """

    user_id: int
    old_password: str
    new_password: str


# --------------------------------------------------------------------------- #
# Output DTOs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class UserPublicOut:
    """
    Output DTO representing public-safe user data.

    :param id: User identifier.
    :type id: int
    :param email: Email address.
    :type email: str
    :param username: Username.
    :type username: str
    :param full_name: Optional full name.
    :type full_name: str | None
    """

    id: int
    email: str
    username: str
    full_name: str | None


@dataclass(frozen=True, slots=True)
class UserAuthOut:
    """
    Output DTO for authentication result (minimal identity payload).

    :param id: User identifier.
    :type id: int
    :param email: Login email.
    :type email: str
    :param username: Username.
    :type username: str
    :param full_name: Optional full name.
    :type full_name: str | None
    """

    id: int
    email: str
    username: str
    full_name: str | None
