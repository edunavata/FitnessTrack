"""
DTOs for UserRegistrationService.

Contracts for orchestrating a user self-registration flow that creates
``User`` + ``Subject`` and links them atomically.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.services.identity.dto import UserPublicOut

# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class UserRegistrationIn:
    """
    Input payload for the registration process.

    :param email: Login email (will be normalized to lowercase+trim).
    :type email: str
    :param password: Raw password (the model setter hashes it).
    :type password: str
    :param username: Public handle (unique).
    :type username: str
    :param full_name: Optional real name.
    :type full_name: str | None
    :param idempotent: When ``True`` (default) the process is safe to retry.
    :type idempotent: bool
    :param idempotency_key: Optional external key to back a persistent idempotency store.
    :type idempotency_key: str | None
    """

    email: str
    password: str
    username: str
    full_name: str | None = None
    idempotent: bool = True
    idempotency_key: str | None = None


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class UserRegistrationOut:
    """
    Output summary for the registration process.

    :param user: Public-safe user payload.
    :type user: :class:`UserPublicOut`
    :param subject_id: Created/linked ``Subject`` identifier.
    :type subject_id: int
    :param subject_pseudonym: Pseudonymous UUID of the subject.
    :type subject_pseudonym: :class:`uuid.UUID`
    :param created: ``True`` if new rows were inserted; ``False`` if idempotent hit.
    :type created: bool
    """

    user: UserPublicOut
    subject_id: int
    subject_pseudonym: UUID
    created: bool
