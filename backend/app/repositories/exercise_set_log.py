"""Exercise set log repository exposing persistence-only operations.

The :class:`ExerciseSetLogRepository` extends the generic
:class:`~app.repositories.base.BaseRepository` to provide deterministic listing
and pagination helpers tailored for :class:`app.models.exercise_log.ExerciseSetLog`.
Business logic and transaction management remain responsibilities of services.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from typing import Any, cast

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.models.exercise_log import ExerciseSetLog  # ajusta si tu path es distinto
from app.repositories import base as base_module  # para usar _apply_sorting en queries custom
from app.repositories.base import BaseRepository, Page, Pagination, paginate_select


class ExerciseSetLogRepository(BaseRepository[ExerciseSetLog]):
    """Persist :class:`ExerciseSetLog` records and support read patterns.

    Access helpers stay persistence-focused, offering deterministic pagination
    and whitelisted sorting while handling the unique constraint on
    ``(subject_id, exercise_id, performed_at, set_index)``. Services orchestrate
    transactions and validation.
    """

    model = ExerciseSetLog

    # ----------------------------- Sorting whitelist -----------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        """
        Allow sorting by stable, indexed columns.

        :returns: Public key → ORM attribute mapping.
        """
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "exercise_id": self.model.exercise_id,
            "session_id": self.model.session_id,
            "performed_at": self.model.performed_at,
            "set_index": self.model.set_index,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
        }

    # ----------------------------- Filter whitelist ------------------------------
    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        """
        Restrict equality filters to identifiers and common flags.
        """
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "exercise_id": self.model.exercise_id,
            "session_id": self.model.session_id,
            "planned_set_id": self.model.planned_set_id,
            "is_warmup": self.model.is_warmup,
            "to_failure": self.model.to_failure,
        }

    # ----------------------------- Updatable whitelist ---------------------------
    def _updatable_fields(self) -> set[str]:
        """
        Fail-closed: immutable identifiers/keys; allow updating actuals and flags.

        Immutable here: subject_id, exercise_id, performed_at, set_index.
        """
        return {
            "session_id",
            "planned_set_id",
            "is_warmup",
            "to_failure",
            "actual_weight_kg",
            "actual_reps",
            "actual_rir",
            "actual_rpe",
            "actual_tempo",
            "actual_rest_s",
            "notes",
        }

    # ----------------------------- Default eager loading -------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        """
        The mapped relationships already use lazy='selectin' on the model,
        so we can leave this as a no-op to keep listings lean.
        """
        return stmt

    # --------------------------------- Creates -----------------------------------
    def create_log(
        self,
        *,
        subject_id: int,
        exercise_id: int,
        performed_at: datetime,
        set_index: int,
        session_id: int | None = None,
        planned_set_id: int | None = None,
        is_warmup: bool = False,
        to_failure: bool = False,
        actual_weight_kg: float | None = None,
        actual_reps: int | None = None,
        actual_rir: int | None = None,
        actual_rpe: float | None = None,
        actual_tempo: str | None = None,
        actual_rest_s: int | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> ExerciseSetLog:
        """Create and stage a new set log entry.

        Attribute assignment is used so that SQLAlchemy validators on the model
        are triggered consistently.

        :param subject_id: Identifier of the performing subject.
        :type subject_id: int
        :param exercise_id: Identifier of the exercise performed.
        :type exercise_id: int
        :param performed_at: Timestamp when the set was performed.
        :type performed_at: datetime.datetime
        :param set_index: Ordinal of the set within the session/exercise.
        :type set_index: int
        :param session_id: Optional workout session identifier.
        :type session_id: int | None
        :param planned_set_id: Optional reference to the planned set.
        :type planned_set_id: int | None
        :param is_warmup: Whether the set is a warm-up.
        :type is_warmup: bool
        :param to_failure: Whether the set went to failure.
        :type to_failure: bool
        :param actual_weight_kg: Actual lifted weight in kilograms.
        :type actual_weight_kg: float | None
        :param actual_reps: Actual repetitions performed.
        :type actual_reps: int | None
        :param actual_rir: Actual reps-in-reserve.
        :type actual_rir: int | None
        :param actual_rpe: Actual rate of perceived exertion.
        :type actual_rpe: float | None
        :param actual_tempo: Tempo notation captured for the set.
        :type actual_tempo: str | None
        :param actual_rest_s: Rest duration after the set in seconds.
        :type actual_rest_s: int | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging the row.
        :type flush: bool
        :returns: The staged :class:`ExerciseSetLog` instance.
        :rtype: ExerciseSetLog
        """
        row = self.model(
            subject_id=subject_id,
            exercise_id=exercise_id,
            performed_at=performed_at,
            set_index=set_index,
            session_id=session_id,  # triggers validator (subject/session match)
            planned_set_id=planned_set_id,
            is_warmup=is_warmup,
            to_failure=to_failure,
            actual_weight_kg=actual_weight_kg,
            actual_reps=actual_reps,
            actual_rir=actual_rir,
            actual_rpe=actual_rpe,
            actual_tempo=actual_tempo,
            actual_rest_s=actual_rest_s,
            notes=notes,
        )
        self.session.add(row)
        if flush:
            self.flush()
        return row

    # --------------------------------- Upsert ------------------------------------
    def upsert_log(
        self,
        *,
        subject_id: int,
        exercise_id: int,
        performed_at: datetime,
        set_index: int,
        # updatable fields:
        session_id: int | None = None,
        planned_set_id: int | None = None,
        is_warmup: bool | None = None,
        to_failure: bool | None = None,
        actual_weight_kg: float | None = None,
        actual_reps: int | None = None,
        actual_rir: int | None = None,
        actual_rpe: float | None = None,
        actual_tempo: str | None = None,
        actual_rest_s: int | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> ExerciseSetLog:
        """Insert or update a set log by its composite unique key.

        Keys are immutable; only provided non-``None`` fields are assigned on
        existing rows.

        :param subject_id: Identifier of the performing subject.
        :type subject_id: int
        :param exercise_id: Identifier of the exercise performed.
        :type exercise_id: int
        :param performed_at: Timestamp when the set was performed.
        :type performed_at: datetime.datetime
        :param set_index: Ordinal of the set within the session/exercise.
        :type set_index: int
        :param session_id: Optional workout session identifier.
        :type session_id: int | None
        :param planned_set_id: Optional reference to the planned set.
        :type planned_set_id: int | None
        :param is_warmup: Optional warm-up flag to assign.
        :type is_warmup: bool | None
        :param to_failure: Optional failure flag to assign.
        :type to_failure: bool | None
        :param actual_weight_kg: Actual lifted weight in kilograms.
        :type actual_weight_kg: float | None
        :param actual_reps: Actual repetitions performed.
        :type actual_reps: int | None
        :param actual_rir: Actual reps-in-reserve.
        :type actual_rir: int | None
        :param actual_rpe: Actual rate of perceived exertion.
        :type actual_rpe: float | None
        :param actual_tempo: Tempo notation captured for the set.
        :type actual_tempo: str | None
        :param actual_rest_s: Rest duration after the set in seconds.
        :type actual_rest_s: int | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging changes.
        :type flush: bool
        :returns: The inserted or updated :class:`ExerciseSetLog` instance.
        :rtype: ExerciseSetLog
        """
        stmt = select(self.model).where(
            and_(
                self.model.subject_id == subject_id,
                self.model.exercise_id == exercise_id,
                self.model.performed_at == performed_at,
                self.model.set_index == set_index,
            )
        )
        existing = self.session.execute(stmt).scalars().first()
        if existing is None:
            # create new
            row = self.create_log(
                subject_id=subject_id,
                exercise_id=exercise_id,
                performed_at=performed_at,
                set_index=set_index,
                session_id=session_id,
                planned_set_id=planned_set_id,
                is_warmup=is_warmup or False,
                to_failure=to_failure or False,
                actual_weight_kg=actual_weight_kg,
                actual_reps=actual_reps,
                actual_rir=actual_rir,
                actual_rpe=actual_rpe,
                actual_tempo=actual_tempo,
                actual_rest_s=actual_rest_s,
                notes=notes,
                flush=flush,
            )
            return row

        # Update only provided fields (None means "leave as is")
        row = cast(ExerciseSetLog, existing)
        updates: dict[str, Any] = {}
        if session_id is not None:
            updates["session_id"] = session_id
        if planned_set_id is not None:
            updates["planned_set_id"] = planned_set_id
        if is_warmup is not None:
            updates["is_warmup"] = is_warmup
        if to_failure is not None:
            updates["to_failure"] = to_failure
        if actual_weight_kg is not None:
            updates["actual_weight_kg"] = actual_weight_kg
        if actual_reps is not None:
            updates["actual_reps"] = actual_reps
        if actual_rir is not None:
            updates["actual_rir"] = actual_rir
        if actual_rpe is not None:
            updates["actual_rpe"] = actual_rpe
        if actual_tempo is not None:
            updates["actual_tempo"] = actual_tempo
        if actual_rest_s is not None:
            updates["actual_rest_s"] = actual_rest_s
        if notes is not None:
            updates["notes"] = notes

        if updates:
            self.assign_updates(row, updates, strict=True, flush=flush)
        return row

    # ----------------------------- Subject queries ------------------------------
    def list_for_subject(
        self,
        subject_id: int,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        exercise_id: int | None = None,
        session_id: int | None = None,
        sort: Iterable[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExerciseSetLog]:
        """List logs for a subject with optional filters.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param date_from: Inclusive lower bound for ``performed_at`` (date).
        :type date_from: datetime.date | None
        :param date_to: Inclusive upper bound for ``performed_at`` (date).
        :type date_to: datetime.date | None
        :param exercise_id: Optional exercise filter.
        :type exercise_id: int | None
        :param session_id: Optional workout session filter.
        :type session_id: int | None
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :param limit: Optional limit for manual pagination.
        :type limit: int | None
        :param offset: Optional offset for manual pagination.
        :type offset: int | None
        :returns: Ordered list of log entries.
        :rtype: list[ExerciseSetLog]
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            # Include the entire ``date_from`` day by converting to a datetime lower bound
            start_dt = datetime.combine(date_from, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.performed_at >= start_dt)
        if date_to is not None:
            # Inclusive upper bound by moving to the next day and using < comparison
            next_day = date_to + timedelta(days=1)
            end_dt = datetime.combine(next_day, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.performed_at < end_dt)

        if exercise_id is not None:
            stmt = stmt.where(self.model.exercise_id == exercise_id)
        if session_id is not None:
            stmt = stmt.where(self.model.session_id == session_id)

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
        exercise_id: int | None = None,
        session_id: int | None = None,
        with_total: bool = True,
    ) -> Page[ExerciseSetLog]:
        """Paginate logs for a subject with optional filters.

        :param pagination: Pagination parameters and sort tokens.
        :type pagination: Pagination
        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param date_from: Inclusive lower bound for ``performed_at`` (date).
        :type date_from: datetime.date | None
        :param date_to: Inclusive upper bound for ``performed_at`` (date).
        :type date_to: datetime.date | None
        :param exercise_id: Optional exercise filter.
        :type exercise_id: int | None
        :param session_id: Optional workout session filter.
        :type session_id: int | None
        :param with_total: Whether to compute the total row count.
        :type with_total: bool
        :returns: Page with log entries respecting deterministic ordering.
        :rtype: Page[ExerciseSetLog]
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            start_dt = datetime.combine(date_from, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.performed_at >= start_dt)
        if date_to is not None:
            next_day = date_to + timedelta(days=1)
            end_dt = datetime.combine(next_day, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.performed_at < end_dt)
        if exercise_id is not None:
            stmt = stmt.where(self.model.exercise_id == exercise_id)
        if session_id is not None:
            stmt = stmt.where(self.model.session_id == session_id)

        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), pagination.sort, pk_attr=self._pk_attr()
        )

        items, total = paginate_select(
            self.session,
            stmt,
            page=pagination.page,
            limit=pagination.limit,
            with_total=with_total,
        )
        return Page(
            items=items,
            total=total if with_total else 0,
            page=pagination.page,
            limit=pagination.limit,
        )

    # ------------------------------ Session queries -----------------------------
    def list_for_session(
        self, session_id: int, *, sort: Iterable[str] | None = None
    ) -> list[ExerciseSetLog]:
        """List logs linked to a specific workout session.

        :param session_id: Identifier of the workout session.
        :type session_id: int
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Ordered list of log entries.
        :rtype: list[ExerciseSetLog]
        """
        stmt = select(self.model).where(self.model.session_id == session_id)
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    # ------------------------------ Latest helper ------------------------------
    def latest_for_subject_exercise(
        self, subject_id: int, exercise_id: int
    ) -> ExerciseSetLog | None:
        """Return the most recent log for a subject/exercise pair.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param exercise_id: Identifier of the exercise.
        :type exercise_id: int
        :returns: Latest log entry or ``None`` when no records exist.
        :rtype: ExerciseSetLog | None
        """
        stmt = select(self.model).where(
            and_(self.model.subject_id == subject_id, self.model.exercise_id == exercise_id)
        )
        # Most recent first; tie-break by set_index DESC; PK ASC final tiebreaker.
        stmt = base_module._apply_sorting(
            stmt,
            {
                "performed_at": self.model.performed_at,
                "set_index": self.model.set_index,
                "id": self.model.id,
            },
            ["-performed_at", "-set_index"],
            pk_attr=self._pk_attr(),
        )
        result = self.session.execute(stmt.limit(1)).scalars().first()
        return cast(ExerciseSetLog | None, result)
