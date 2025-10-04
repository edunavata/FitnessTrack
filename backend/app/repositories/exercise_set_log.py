# backend/app/repositories/exercise_set_log.py
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
    """
    Persistence-only repository for :class:`app.models.exercise_log.ExerciseSetLog`.

    - Read patterns: by subject + date range, by session, latest by subject/exercise.
    - Write patterns: create and upsert by the unique key
      (subject_id, exercise_id, performed_at, set_index).

    No business rules, no commits; services own transactions.
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
        """
        Create a new set log row. Validators on the model are triggered via setattr.
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
        """
        Insert or update by unique key (subject_id, exercise_id, performed_at, set_index).

        Keys are immutable; only non-None updatable fields are assigned.
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
        """
        List logs for a subject with optional date range, exercise and session filters.
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)

        if date_from is not None:
            # include whole day: convert date->datetime low bound
            start_dt = datetime.combine(date_from, datetime.min.time()).astimezone()
            stmt = stmt.where(self.model.performed_at >= start_dt)
        if date_to is not None:
            # inclusive upper bound for date: next day min - 1ns
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
        """
        Paginate logs for a subject with optional filters and date range.
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
        """
        List all logs belonging to a given WorkoutSession.
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
        """
        Return the latest log for a subject/exercise by performed_at DESC, set_index DESC.
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
