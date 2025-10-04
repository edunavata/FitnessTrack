"""Workout session repository exposing persistence-focused helpers.

The :class:`WorkoutSessionRepository` extends
:class:`~app.repositories.base.BaseRepository` to manage
:class:`app.models.workout.WorkoutSession`. It focuses on deterministic
pagination, range queries and safe updates, leaving transactions to the service
layer.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from typing import Any, cast

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.models.workout import WorkoutSession
from app.repositories import base as base_module
from app.repositories.base import BaseRepository, Page, Pagination, paginate_select


class WorkoutSessionRepository(BaseRepository[WorkoutSession]):
    """Persist :class:`WorkoutSession` rows and expose range/listing helpers.

    The repository honours the logical unique key ``(subject_id, workout_date)``
    and provides convenience methods for deterministic queries by subject,
    cycle and date range. Eager loading defaults remain lean to avoid excessive
    joins; services orchestrate transactions and business rules.
    """

    model = WorkoutSession

    # ---------------------------- Whitelists ----------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "workout_date": self.model.workout_date,
            "status": self.model.status,
            "cycle_id": self.model.cycle_id,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
        }

    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        return {
            "subject_id": self.model.subject_id,
            "cycle_id": self.model.cycle_id,
            "routine_day_id": self.model.routine_day_id,
            "status": self.model.status,
        }

    def _updatable_fields(self) -> set[str]:
        # Do not allow updates to the logical unique key (subject_id, workout_date).
        return {
            "status",
            "cycle_id",
            "routine_day_id",
            "location",
            "perceived_fatigue",
            "bodyweight_kg",
            "notes",
        }

    # ---------------------------- Eager loading ----------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        # Relationships already use ``lazy="selectin"`` on the mapper; keep lean.
        return stmt

    # ---------------------------- Lookups ----------------------------
    def get_by_unique(self, subject_id: int, workout_date: datetime) -> WorkoutSession | None:
        """Return a session identified by the logical unique key.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param workout_date: Datetime representing the scheduled workout date.
        :type workout_date: datetime.datetime
        :returns: Matching session or ``None`` when absent.
        :rtype: WorkoutSession | None
        """
        stmt = select(self.model).where(
            and_(self.model.subject_id == subject_id, self.model.workout_date == workout_date)
        )
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(WorkoutSession | None, result)

    # ---------------------------- Mutations ----------------------------
    def create_session(
        self,
        *,
        subject_id: int,
        workout_date: datetime,
        status: str | None = None,
        routine_day_id: int | None = None,
        cycle_id: int | None = None,
        location: str | None = None,
        perceived_fatigue: int | None = None,
        bodyweight_kg: float | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> WorkoutSession:
        """Create and stage a new workout session.

        Assignment triggers SQLAlchemy validators (e.g., cycle subject matching)
        defined on the model.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param workout_date: Datetime representing the scheduled workout date.
        :type workout_date: datetime.datetime
        :param status: Optional explicit status; defaults to ``"PENDING"``.
        :type status: str | None
        :param routine_day_id: Optional link to a planned routine day.
        :type routine_day_id: int | None
        :param cycle_id: Optional training cycle association.
        :type cycle_id: int | None
        :param location: Optional location string.
        :type location: str | None
        :param perceived_fatigue: Optional fatigue indicator.
        :type perceived_fatigue: int | None
        :param bodyweight_kg: Optional body weight measurement.
        :type bodyweight_kg: float | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging the row.
        :type flush: bool
        :returns: The staged :class:`WorkoutSession` entity.
        :rtype: WorkoutSession
        """
        row = self.model(
            subject_id=subject_id,
            workout_date=workout_date,
            status=(status or "PENDING"),
            routine_day_id=routine_day_id,
            cycle_id=cycle_id,
            location=location,
            perceived_fatigue=perceived_fatigue,
            bodyweight_kg=bodyweight_kg,
            notes=notes,
        )
        self.session.add(row)
        if flush:
            self.flush()
        return row

    def upsert_by_date(
        self,
        *,
        subject_id: int,
        workout_date: datetime,
        # updatable fields:
        status: str | None = None,
        routine_day_id: int | None = None,
        cycle_id: int | None = None,
        location: str | None = None,
        perceived_fatigue: int | None = None,
        bodyweight_kg: float | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> WorkoutSession:
        """Insert or update a session by ``(subject_id, workout_date)``.

        Logical key fields remain immutable; only provided non-``None`` values
        are assigned.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param workout_date: Datetime representing the scheduled workout date.
        :type workout_date: datetime.datetime
        :param status: Optional status to set.
        :type status: str | None
        :param routine_day_id: Optional link to a planned routine day.
        :type routine_day_id: int | None
        :param cycle_id: Optional training cycle association.
        :type cycle_id: int | None
        :param location: Optional location string.
        :type location: str | None
        :param perceived_fatigue: Optional fatigue indicator.
        :type perceived_fatigue: int | None
        :param bodyweight_kg: Optional body weight measurement.
        :type bodyweight_kg: float | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after mutation.
        :type flush: bool
        :returns: The inserted or updated :class:`WorkoutSession` entity.
        :rtype: WorkoutSession
        """
        row = self.get_by_unique(subject_id, workout_date)
        if row is None:
            return self.create_session(
                subject_id=subject_id,
                workout_date=workout_date,
                status=(status or "PENDING"),
                routine_day_id=routine_day_id,
                cycle_id=cycle_id,
                location=location,
                perceived_fatigue=perceived_fatigue,
                bodyweight_kg=bodyweight_kg,
                notes=notes,
                flush=flush,
            )

        updates: dict[str, Any] = {}
        if status is not None:
            updates["status"] = status
        if routine_day_id is not None:
            updates["routine_day_id"] = routine_day_id
        if cycle_id is not None:
            updates["cycle_id"] = cycle_id  # disparará validador del modelo
        if location is not None:
            updates["location"] = location
        if perceived_fatigue is not None:
            updates["perceived_fatigue"] = perceived_fatigue
        if bodyweight_kg is not None:
            updates["bodyweight_kg"] = bodyweight_kg
        if notes is not None:
            updates["notes"] = notes

        if updates:
            self.assign_updates(row, updates, strict=True, flush=flush)
        return row

    def attach_to_cycle(
        self, ws_id: int, cycle_id: int | None, *, flush: bool = True
    ) -> WorkoutSession:
        """Associate or detach a session from a cycle.

        :param ws_id: Identifier of the workout session.
        :type ws_id: int
        :param cycle_id: Cycle identifier to attach or ``None`` to detach.
        :type cycle_id: int | None
        :param flush: Whether to flush the session after mutation.
        :type flush: bool
        :returns: The mutated session instance.
        :rtype: WorkoutSession
        :raises ValueError: If the session does not exist.
        """
        row = self.get(ws_id)
        if not row:
            raise ValueError(f"WorkoutSession {ws_id} not found.")
        self.assign_updates(row, {"cycle_id": cycle_id}, strict=True, flush=flush)
        return row

    def mark_completed(self, ws_id: int, *, flush: bool = True) -> WorkoutSession:
        """Mark the session status as ``"COMPLETED"``.

        :param ws_id: Identifier of the workout session.
        :type ws_id: int
        :param flush: Whether to flush the session after mutation.
        :type flush: bool
        :returns: The mutated session instance.
        :rtype: WorkoutSession
        :raises ValueError: If the session does not exist.
        """
        row = self.get(ws_id)
        if not row:
            raise ValueError(f"WorkoutSession {ws_id} not found.")
        self.assign_updates(row, {"status": "COMPLETED"}, strict=True, flush=flush)
        return row

    # ---------------------------- Queries ----------------------------
    def list_for_subject(
        self,
        subject_id: int,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        sort: Iterable[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[WorkoutSession]:
        """List sessions for a subject with an optional date range.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param date_from: Inclusive lower bound for ``workout_date`` (date component).
        :type date_from: datetime.date | None
        :param date_to: Inclusive upper bound for ``workout_date`` (date component).
        :type date_to: datetime.date | None
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :param limit: Optional limit for manual pagination.
        :type limit: int | None
        :param offset: Optional offset for manual pagination.
        :type offset: int | None
        :returns: Ordered list of sessions.
        :rtype: list[WorkoutSession]
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            start_dt = datetime.combine(date_from, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.workout_date >= start_dt)
        if date_to is not None:
            next_day = date_to + timedelta(days=1)
            end_dt = datetime.combine(next_day, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.workout_date < end_dt)

        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
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
    ) -> Page[WorkoutSession]:
        """Paginate sessions for a subject with optional date filters.

        :param pagination: Pagination parameters and sort tokens.
        :type pagination: Pagination
        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param date_from: Inclusive lower bound for ``workout_date`` (date component).
        :type date_from: datetime.date | None
        :param date_to: Inclusive upper bound for ``workout_date`` (date component).
        :type date_to: datetime.date | None
        :param with_total: Whether to compute the total row count.
        :type with_total: bool
        :returns: Page containing sessions and metadata.
        :rtype: Page[WorkoutSession]
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            start_dt = datetime.combine(date_from, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.workout_date >= start_dt)
        if date_to is not None:
            next_day = date_to + timedelta(days=1)
            end_dt = datetime.combine(next_day, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.workout_date < end_dt)

        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), pagination.sort, pk_attr=self._pk_attr()
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

    def list_for_cycle(
        self, cycle_id: int, *, sort: Iterable[str] | None = None
    ) -> list[WorkoutSession]:
        """List sessions that belong to a specific cycle.

        :param cycle_id: Identifier of the cycle.
        :type cycle_id: int
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Ordered list of sessions associated with the cycle.
        :rtype: list[WorkoutSession]
        """
        stmt: Select[Any] = select(self.model).where(self.model.cycle_id == cycle_id)
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())
