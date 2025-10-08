"""
SubjectMetricsService
=====================

Application service for the time-series aggregate ``SubjectBodyMetrics``.

Responsibilities
----------------
- Upsert daily metrics identified by ``(subject_id, measured_on)``.
- Retrieve a single row by unique key.
- List and paginate with optional date-range filters.
- Delete a row by unique key.

Notes
-----
- Read operations use ``ro_uow()``; write operations use ``rw_uow()``.
- Errors are raised via domain exceptions from ``_shared.errors``.
"""

from __future__ import annotations

from app.models.subject import SubjectBodyMetrics
from app.repositories.subject_body_metrics import SubjectBodyMetricsRepository
from app.services._shared.base import BaseService
from app.services._shared.dto import PageMeta
from app.services._shared.errors import NotFoundError
from app.services.subject_metrics.dto import (
    MetricsDeleteIn,
    MetricsGetIn,
    MetricsListIn,
    MetricsListOut,
    MetricsRowOut,
    MetricsUpsertIn,
)


class SubjectMetricsService(BaseService):
    """
    Service orchestrating persistence-only operations of ``SubjectBodyMetrics``.
    """

    # ------------------------------------------------------------------ #
    # Upsert
    # ------------------------------------------------------------------ #

    def upsert(self, dto: MetricsUpsertIn) -> MetricsRowOut:
        """
        Insert or update a metrics row by ``(subject_id, measured_on)``.

        :param dto: Upsert DTO.
        :type dto: :class:`MetricsUpsertIn`
        :returns: Persisted row as output DTO.
        :rtype: :class:`MetricsRowOut`
        :raises PreconditionFailedError: If ``if_match`` provided and mismatches.
        """
        with self.rw_uow() as uow:
            repo: SubjectBodyMetricsRepository = uow.subject_body_metrics

            # If if_match is provided, and row exists, validate ETag first
            if dto.if_match is not None:
                existing = self._get_existing_row(repo, dto.subject_id, dto.measured_on)
                if existing is not None:
                    current = self._maybe_etag(existing)
                    self.ensure_if_match(dto.if_match, current or "")
                # If not existing, proceed; if-match on non-existing row would typically
                # be handled at API layer (If-None-Match), but we keep it permissive here.

            row = repo.upsert_by_day(
                subject_id=dto.subject_id,
                measured_on=dto.measured_on,
                weight_kg=dto.weight_kg,
                bodyfat_pct=dto.bodyfat_pct,
                resting_hr=dto.resting_hr,
                notes=dto.notes,
                flush=True,
            )
            return self._to_row_out(row)

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #

    def get(self, dto: MetricsGetIn) -> MetricsRowOut:
        """
        Retrieve a single metrics row by unique key.

        :param dto: Get DTO.
        :type dto: :class:`MetricsGetIn`
        :returns: Metrics row DTO.
        :rtype: :class:`MetricsRowOut`
        :raises NotFoundError: If row does not exist.
        """
        with self.ro_uow() as uow:
            repo: SubjectBodyMetricsRepository = uow.subject_body_metrics
            row = self._get_existing_row(repo, dto.subject_id, dto.measured_on)
            if row is None:
                raise NotFoundError(
                    "SubjectBodyMetrics",
                    f"{dto.subject_id}@{dto.measured_on.isoformat()}",
                )
            return self._to_row_out(row)

    # ------------------------------------------------------------------ #
    # Listing
    # ------------------------------------------------------------------ #

    def list(self, dto: MetricsListIn) -> MetricsListOut:
        """
        List/paginate metrics for a subject and optional date range.

        :param dto: List DTO with pagination and range.
        :type dto: :class:`MetricsListIn`
        :returns: Paginated list output.
        :rtype: :class:`MetricsListOut`
        """
        with self.ro_uow() as uow:
            repo: SubjectBodyMetricsRepository = uow.subject_body_metrics

            pagination = self.ensure_pagination(
                page=dto.pagination.page, limit=dto.pagination.limit, sort=dto.pagination.sort
            )

            page = repo.paginate_for_subject(
                pagination,
                subject_id=dto.subject_id,
                date_from=dto.date_from,
                date_to=dto.date_to,
                with_total=dto.with_total,
            )

            items = [self._to_row_out(r) for r in page.items]
            meta = PageMeta(
                page=page.page,
                limit=page.limit,
                total=page.total,
                has_prev=page.page > 1,
                has_next=(page.page * page.limit) < page.total if dto.with_total else False,
            )
            return MetricsListOut(items=items, meta=meta)

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete(self, dto: MetricsDeleteIn) -> None:
        """
        Delete a metrics row by unique key (idempotent).

        :param dto: Delete DTO with optional ETag.
        :type dto: :class:`MetricsDeleteIn`
        :returns: ``None``.
        :rtype: None
        :raises PreconditionFailedError: If ``if_match`` provided and mismatches.
        """
        with self.rw_uow() as uow:
            repo: SubjectBodyMetricsRepository = uow.subject_body_metrics
            row = self._get_existing_row(repo, dto.subject_id, dto.measured_on)
            if row is None:
                # idempotent delete - nothing to do
                return

            if dto.if_match is not None:
                current = self._maybe_etag(row)
                self.ensure_if_match(dto.if_match, current or "")

            repo.delete(row)
            # UoW commits on exit

    # ------------------------------------------------------------------ #
    # Internals / mapping
    # ------------------------------------------------------------------ #

    def _get_existing_row(
        self,
        repo: SubjectBodyMetricsRepository,
        subject_id: int,
        measured_on,
    ) -> SubjectBodyMetrics | None:
        """
        Helper to locate a row by unique key.

        :param repo: Metrics repository.
        :type repo: :class:`SubjectBodyMetricsRepository`
        :param subject_id: Subject identifier.
        :type subject_id: int
        :param measured_on: Measurement date.
        :type measured_on: :class:`datetime.date`
        :returns: ORM row or ``None``.
        :rtype: SubjectBodyMetrics | None
        """
        # We can use a simple equality filter via list() or write a targeted query.
        # Reusing list() keeps code minimal and typed.
        rows = repo.list(
            filters={"subject_id": subject_id, "measured_on": measured_on},
            limit=1,
            offset=0,
        )
        return rows[0] if rows else None

    def _maybe_etag(self, obj: object) -> str | None:
        """
        Return an ETag computed by the domain object when supported.

        :param obj: Domain entity instance.
        :type obj: object
        :returns: ETag or ``None``.
        :rtype: str | None
        """
        compute = getattr(obj, "compute_etag", None)
        if callable(compute):
            try:
                return str(compute())
            except Exception:
                return None
        return None

    def _to_row_out(self, row) -> MetricsRowOut:
        """
        Map ORM ``SubjectBodyMetrics`` to :class:`MetricsRowOut`.

        :param row: ORM metrics row.
        :type row: :class:`app.models.subject.SubjectBodyMetrics`
        :returns: Output DTO.
        :rtype: :class:`MetricsRowOut`
        """
        return MetricsRowOut(
            id=row.id,
            subject_id=row.subject_id,
            measured_on=row.measured_on,
            weight_kg=row.weight_kg,
            bodyfat_pct=row.bodyfat_pct,
            resting_hr=row.resting_hr,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
            etag=self._maybe_etag(row),
        )
