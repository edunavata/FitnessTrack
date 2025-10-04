# backend/app/repositories/subject_body_metrics.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any, cast

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.models.subject import SubjectBodyMetrics
from app.repositories import base as base_module
from app.repositories.base import BaseRepository, Page, Pagination, paginate_select

# Re-exported for tests expecting module-level symbol
apply_sorting = base_module._apply_sorting


class SubjectBodyMetricsRepository(BaseRepository[SubjectBodyMetrics]):
    """
    Persistence-only repository for :class:`app.models.subject.SubjectBodyMetrics`.

    Focused on time-series access patterns:
    - Range queries by ``measured_on``.
    - Deterministic pagination with PK tiebreaker.
    - Idempotent upsert by ``(subject_id, measured_on)``.
    """

    model = SubjectBodyMetrics

    # ---- Sorting whitelist --------------------------------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        """
        Allow sorting by stable, indexed columns.

        :returns: Public key → ORM attribute mapping.
        :rtype: Mapping[str, InstrumentedAttribute]
        """
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "measured_on": self.model.measured_on,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
        }

    # ---- Filter whitelist (equality-only) -----------------------------------
    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        """
        Restrict equality filters to core identifiers.

        :returns: Public key → ORM attribute mapping.
        :rtype: Mapping[str, InstrumentedAttribute] | None
        """
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "measured_on": self.model.measured_on,
        }

    # ---- Updatable whitelist -------------------------------------------------
    def _updatable_fields(self) -> set[str]:
        """
        Allow-list of updatable scalar fields for safe mass-assignment.

        :returns: Set of field names.
        :rtype: set[str]
        """
        return {
            "weight_kg",
            "bodyfat_pct",
            "resting_hr",
            "notes",
        }

    # ---- Default eager loading ----------------------------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        """
        No default eager loading is necessary for time-series rows.

        Keep the row lean; relations are simple and loaded on demand.
        """
        return stmt

    # ----------------------------- Range queries ------------------------------
    def list_for_subject(
        self,
        subject_id: int,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        sort: Iterable[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[SubjectBodyMetrics]:
        """
        List metrics for a subject with optional date-range filtering.

        :param subject_id: Subject identifier.
        :type subject_id: int
        :param date_from: Inclusive lower bound for ``measured_on``.
        :type date_from: :class:`datetime.date` | None
        :param date_to: Inclusive upper bound for ``measured_on``.
        :type date_to: :class:`datetime.date` | None
        :param sort: Public sort tokens (e.g., ``["-measured_on"]``).
        :type sort: Iterable[str] | None
        :param limit: Optional limit.
        :type limit: int | None
        :param offset: Optional offset.
        :type offset: int | None
        :returns: List of rows.
        :rtype: list[:class:`app.models.subject.SubjectBodyMetrics`]
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            stmt = stmt.where(self.model.measured_on >= date_from)
        if date_to is not None:
            stmt = stmt.where(self.model.measured_on <= date_to)

        # Reuse BaseRepository sorting (PK tiebreaker included)
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt,
            self._sortable_fields(),
            sort or [],
            pk_attr=self._pk_attr(),
        )

        if limit is not None:
            stmt = stmt.limit(int(limit))
        if offset is not None:
            stmt = stmt.offset(int(offset))

        return list(self.session.execute(stmt).scalars().all())

    def paginate_for_subject(
        self,
        pagination: Pagination,
        *,
        subject_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        with_total: bool = True,
    ) -> Page[SubjectBodyMetrics]:
        """
        Paginate metrics for a subject with optional date range.

        :param pagination: Pagination parameters.
        :type pagination: :class:`app.repositories.base.Pagination`
        :param subject_id: Subject identifier.
        :type subject_id: int
        :param date_from: Inclusive lower bound for ``measured_on``.
        :type date_from: :class:`datetime.date` | None
        :param date_to: Inclusive upper bound for ``measured_on``.
        :type date_to: :class:`datetime.date` | None
        :param with_total: Whether to compute total rows.
        :type with_total: bool
        :returns: Page with items and metadata.
        :rtype: :class:`app.repositories.base.Page`
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            stmt = stmt.where(self.model.measured_on >= date_from)
        if date_to is not None:
            stmt = stmt.where(self.model.measured_on <= date_to)

        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt,
            self._sortable_fields(),
            pagination.sort,
            pk_attr=self._pk_attr(),
        )

        items, total = paginate_select(
            self.session, stmt, page=pagination.page, limit=pagination.limit, with_total=with_total
        )
        return Page(
            items=items,
            total=total if with_total else 0,
            page=pagination.page,
            limit=pagination.limit,
        )

    # ------------------------------- Upsert -----------------------------------
    def upsert_by_day(
        self,
        *,
        subject_id: int,
        measured_on: date,
        weight_kg: float | None = None,
        bodyfat_pct: float | None = None,
        resting_hr: int | None = None,
        notes: str | None = None,
        strict: bool = True,
        flush: bool = True,
    ) -> SubjectBodyMetrics:
        """
        Insert or update a row identified by ``(subject_id, measured_on)``.

        Uses model validators by assigning attributes (``setattr``).

        :param subject_id: Subject identifier.
        :type subject_id: int
        :param measured_on: Measurement date (unique per subject).
        :type measured_on: :class:`datetime.date`
        :param weight_kg: Optional weight in kilograms.
        :type weight_kg: float | None
        :param bodyfat_pct: Optional body fat percentage.
        :type bodyfat_pct: float | None
        :param resting_hr: Optional resting heart rate (bpm).
        :type resting_hr: int | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param strict: When ``True``, unknown keys raise ``ValueError`` (not used here).
        :type strict: bool
        :param flush: Whether to flush changes after mutation.
        :type flush: bool
        :returns: The upserted row.
        :rtype: :class:`app.models.subject.SubjectBodyMetrics`
        """
        # Try to find an existing row
        stmt = select(self.model).where(
            and_(self.model.subject_id == subject_id, self.model.measured_on == measured_on)
        )
        row = cast(SubjectBodyMetrics | None, self.session.execute(stmt).scalars().first())

        if row is None:
            # Create new row
            row = self.model(
                subject_id=subject_id,
                measured_on=measured_on,
            )
            self.session.add(row)

        # Assign via setattr to trigger validators on the model
        if weight_kg is not None:
            row.weight_kg = weight_kg
        if bodyfat_pct is not None:
            row.bodyfat_pct = bodyfat_pct
        if resting_hr is not None:
            row.resting_hr = resting_hr
        if notes is not None:
            row.notes = notes

        if flush:
            self.flush()
        return row
