"""
DTOs for SubjectService.

These DTOs define framework-agnostic contracts between the API layer
and the application service managing the ``Subject`` aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.services._shared.dto import PageMeta, PaginationIn

# --------------------------------------------------------------------------- #
# Input DTOs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SubjectCreateIn:
    """
    Input DTO for creating a new subject.

    :param user_id: Optional user identifier to link upon creation.
    :type user_id: int | None
    """

    user_id: int | None = None


@dataclass(frozen=True, slots=True)
class SubjectLinkUserIn:
    """
    Input DTO for linking a subject to a user.

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param user_id: User identifier to link.
    :type user_id: int
    :param if_match: Optional ETag for optimistic concurrency.
    :type if_match: str | None
    """

    subject_id: int
    user_id: int
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class SubjectUnlinkUserIn:
    """
    Input DTO for unlinking a subject from its user.

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param if_match: Optional ETag for optimistic concurrency.
    :type if_match: str | None
    """

    subject_id: int
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class SubjectUpdateProfileIn:
    """
    Input DTO for updating the subject profile (1:1).

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param sex: Sex value (enum name) or enum instance.
    :type sex: str | None
    :param birth_year: Optional birth year.
    :type birth_year: int | None
    :param height_cm: Optional height in centimeters.
    :type height_cm: int | None
    :param dominant_hand: Optional dominant hand (<= 10 chars).
    :type dominant_hand: str | None
    :param if_match: Optional ETag for optimistic concurrency over the profile.
    :type if_match: str | None
    """

    subject_id: int
    sex: str | None = None
    birth_year: int | None = None
    height_cm: int | None = None
    dominant_hand: str | None = None
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class SubjectGetByPseudonymIn:
    """
    Input DTO for retrieving a subject by pseudonym.

    :param pseudonym: Pseudonymous stable UUID.
    :type pseudonym: :class:`uuid.UUID`
    """

    pseudonym: UUID


@dataclass(frozen=True, slots=True)
class SubjectListIn:
    """
    Input DTO for listing subjects with pagination and optional filters.

    Allowed filters: ``id``, ``user_id``, ``pseudonym``.
    Sort keys follow repository whitelist: ``id``, ``created_at``, ``updated_at``,
    ``user_id``, ``pseudonym``.

    :param pagination: Pagination parameters.
    :type pagination: :class:`PaginationIn`
    :param filters: Optional equality filters.
    :type filters: dict[str, Any] | None
    :param with_total: Whether to compute total rows.
    :type with_total: bool
    """

    pagination: PaginationIn
    filters: dict[str, Any] | None = None
    with_total: bool = True


# --------------------------------------------------------------------------- #
# Output DTOs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SubjectPublicOut:
    """
    Public-safe Subject output.

    :param id: Subject identifier.
    :type id: int
    :param user_id: Linked user identifier or ``None``.
    :type user_id: int | None
    :param pseudonym: Pseudonymous UUID.
    :type pseudonym: :class:`uuid.UUID`
    :param created_at: Creation timestamp.
    :type created_at: :class:`datetime.datetime`
    :param updated_at: Update timestamp.
    :type updated_at: :class:`datetime.datetime`
    :param etag: Optional strong validator for concurrency.
    :type etag: str | None
    """

    id: int
    user_id: int | None
    pseudonym: UUID
    created_at: datetime
    updated_at: datetime
    etag: str | None


@dataclass(frozen=True, slots=True)
class SubjectProfileOut:
    """
    Output DTO representing the subject profile.

    :param sex: Sex enum value or ``None``.
    :type sex: str | None
    :param birth_year: Optional birth year.
    :type birth_year: int | None
    :param height_cm: Optional height in centimeters.
    :type height_cm: int | None
    :param dominant_hand: Optional dominant hand.
    :type dominant_hand: str | None
    :param etag: Optional ETag if available for the profile.
    :type etag: str | None
    """

    sex: str | None
    birth_year: int | None
    height_cm: int | None
    dominant_hand: str | None
    etag: str | None


@dataclass(frozen=True, slots=True)
class SubjectWithProfileOut:
    """
    Subject output composed with its (optional) profile.

    :param subject: Subject public data.
    :type subject: :class:`SubjectPublicOut`
    :param profile: Optional profile data.
    :type profile: :class:`SubjectProfileOut` | None
    """

    subject: SubjectPublicOut
    profile: SubjectProfileOut | None


@dataclass(frozen=True, slots=True)
class SubjectListOut:
    """
    Paginated list output for subjects.

    :param items: List of subjects with optional profiles.
    :type items: list[:class:`SubjectWithProfileOut`]
    :param meta: Pagination metadata.
    :type meta: :class:`PageMeta`
    """

    items: list[SubjectWithProfileOut]
    meta: PageMeta
