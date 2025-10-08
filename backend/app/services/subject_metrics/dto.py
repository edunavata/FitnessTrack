"""
DTOs for SubjectMetricsService.

Contracts between API and the application service managing the
time-series aggregate ``SubjectBodyMetrics``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.services._shared.dto import PageMeta, PaginationIn

# --------------------------------------------------------------------------- #
# Input DTOs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MetricsUpsertIn:
    """
    Upsert a metrics row identified by ``(subject_id, measured_on)``.

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param measured_on: Measurement date (unique per subject).
    :type measured_on: :class:`datetime.date`
    :param weight_kg: Optional weight (kg), non-negative when present.
    :type weight_kg: float | None
    :param bodyfat_pct: Optional body fat percentage in [0, 100].
    :type bodyfat_pct: float | None
    :param resting_hr: Optional resting heart rate (> 0).
    :type resting_hr: int | None
    :param notes: Optional notes.
    :type notes: str | None
    :param if_match: Optional ETag for optimistic concurrency.
    :type if_match: str | None
    """

    subject_id: int
    measured_on: date
    weight_kg: float | None = None
    bodyfat_pct: float | None = None
    resting_hr: int | None = None
    notes: str | None = None
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsGetIn:
    """
    Retrieve a metrics row by unique key.

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param measured_on: Measurement date.
    :type measured_on: :class:`datetime.date`
    """

    subject_id: int
    measured_on: date


@dataclass(frozen=True, slots=True)
class MetricsDeleteIn:
    """
    Delete a metrics row by unique key with optional ETag.

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param measured_on: Measurement date.
    :type measured_on: :class:`datetime.date`
    :param if_match: Optional ETag for optimistic concurrency.
    :type if_match: str | None
    """

    subject_id: int
    measured_on: date
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsListIn:
    """
    List metrics for a subject with optional date range and sorting.

    Sort keys allowed by repository: ``id``, ``subject_id``, ``measured_on``,
    ``created_at``, ``updated_at``.

    :param subject_id: Subject identifier.
    :type subject_id: int
    :param pagination: Pagination parameters.
    :type pagination: :class:`PaginationIn`
    :param date_from: Inclusive lower bound for ``measured_on``.
    :type date_from: :class:`datetime.date` | None
    :param date_to: Inclusive upper bound for ``measured_on``.
    :type date_to: :class:`datetime.date` | None
    :param with_total: Whether to compute total rows.
    :type with_total: bool
    """

    subject_id: int
    pagination: PaginationIn
    date_from: date | None = None
    date_to: date | None = None
    with_total: bool = True


# --------------------------------------------------------------------------- #
# Output DTOs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MetricsRowOut:
    """
    Public-safe representation of a time-series metrics row.

    :param id: Row identifier.
    :type id: int
    :param subject_id: Subject identifier.
    :type subject_id: int
    :param measured_on: Measurement date.
    :type measured_on: :class:`datetime.date`
    :param weight_kg: Optional weight (kg).
    :type weight_kg: float | None
    :param bodyfat_pct: Optional body fat percentage.
    :type bodyfat_pct: float | None
    :param resting_hr: Optional resting heart rate (bpm).
    :type resting_hr: int | None
    :param notes: Optional notes.
    :type notes: str | None
    :param created_at: Creation timestamp.
    :type created_at: :class:`datetime.datetime`
    :param updated_at: Update timestamp.
    :type updated_at: :class:`datetime.datetime`
    :param etag: Optional ETag for concurrency checks.
    :type etag: str | None
    """

    id: int
    subject_id: int
    measured_on: date
    weight_kg: float | None
    bodyfat_pct: float | None
    resting_hr: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    etag: str | None


@dataclass(frozen=True, slots=True)
class MetricsListOut:
    """
    Paginated list of metrics rows.

    :param items: Metrics rows for the page.
    :type items: list[:class:`MetricsRowOut`]
    :param meta: Pagination metadata.
    :type meta: :class:`PageMeta`
    """

    items: list[MetricsRowOut]
    meta: PageMeta
