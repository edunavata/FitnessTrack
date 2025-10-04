"""Routine repositories providing persistence-focused data access helpers.

This module introduces repositories for :class:`app.models.routine.Routine`
and :class:`app.models.routine.SubjectRoutine`, extending the generic
:class:`~app.repositories.base.BaseRepository`. They encapsulate persistence
concerns such as deterministic pagination, whitelist-based sorting and eager
loading while delegating transaction management to higher-level services.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.models.routine import (
    Routine,
    RoutineDay,
    RoutineDayExercise,
    RoutineExerciseSet,
    SubjectRoutine,
)
from app.repositories import base as base_module
from app.repositories.base import BaseRepository, Page, Pagination, paginate_select


class RoutineRepository(BaseRepository[Routine]):
    """Persist :class:`Routine` aggregates and manage hierarchical children.

    The repository focuses on persistence mechanics — deterministic listing,
    safe sorting and selectin-based eager loading of related days, exercises and
    sets. Business rules (such as authorisation) remain in the service layer.
    """

    model = Routine

    # ----------------------------- Whitelists ---------------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        return {
            "id": self.model.id,
            "owner_subject_id": self.model.owner_subject_id,
            "name": self.model.name,
            "is_public": self.model.is_public,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
        }

    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        return {
            "id": self.model.id,
            "owner_subject_id": self.model.owner_subject_id,
            "is_public": self.model.is_public,
            "name": self.model.name,
        }

    def _updatable_fields(self) -> set[str]:
        return {"name", "description", "is_public"}

    # ----------------------------- Eager loading -------------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        """Attach eager loading suited for routine aggregates.

        Collections are loaded via ``selectinload`` to prevent row explosion
        while still materialising the nested structure in a handful of
        roundtrips.

        :param stmt: Base ``SELECT`` statement to augment.
        :type stmt: :class:`sqlalchemy.sql.Select`
        :returns: Statement with eager-loading options applied.
        :rtype: :class:`sqlalchemy.sql.Select`
        """
        return stmt.options(
            selectinload(self.model.days)
            .selectinload(RoutineDay.exercises)
            .selectinload(RoutineDayExercise.sets)
        )

    # ----------------------------- Lookups ------------------------------------
    def get_by_owner_and_name(self, owner_subject_id: int, name: str) -> Routine | None:
        """Retrieve a routine by owner and unique name.

        :param owner_subject_id: Identifier of the owning subject.
        :type owner_subject_id: int
        :param name: Unique routine name per owner.
        :type name: str
        :returns: Matching routine or ``None`` when absent.
        :rtype: Routine | None
        """
        stmt: Select[Any] = select(self.model).where(
            and_(self.model.owner_subject_id == owner_subject_id, self.model.name == name)
        )
        stmt = self._default_eagerload(stmt)
        return cast(Routine | None, self.session.execute(stmt).scalars().first())

    def list_by_owner(
        self, owner_subject_id: int, *, sort: Iterable[str] | None = None
    ) -> list[Routine]:
        """List routines owned by a subject with optional sorting.

        :param owner_subject_id: Identifier of the owning subject.
        :type owner_subject_id: int
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Ordered routines for the owner.
        :rtype: list[Routine]
        """
        stmt: Select[Any] = select(self.model).where(
            self.model.owner_subject_id == owner_subject_id
        )
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_public(self, *, sort: Iterable[str] | None = None) -> list[Routine]:
        """List publicly shared routines.

        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Ordered list of public routines.
        :rtype: list[Routine]
        """
        stmt: Select[Any] = select(self.model).where(self.model.is_public.is_(True))
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    # ----------------------------- Days ---------------------------------------
    def _next_day_index(self, routine_id: int) -> int:
        """Return the next available ``day_index`` for a routine.

        :param routine_id: Identifier of the parent routine.
        :type routine_id: int
        :returns: Next sequential ``day_index`` starting from ``1``.
        :rtype: int
        """
        q = select(func.coalesce(func.max(RoutineDay.day_index), 0) + 1).where(
            RoutineDay.routine_id == routine_id
        )
        return int(self.session.execute(q).scalar_one())

    def add_day(
        self,
        routine_id: int,
        *,
        day_index: int | None = None,
        is_rest: bool = False,
        title: str | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> RoutineDay:
        """Create a routine day, optionally at a specific index.

        :param routine_id: Identifier of the parent routine.
        :type routine_id: int
        :param day_index: Optional explicit day index; ``None`` appends at end.
        :type day_index: int | None
        :param is_rest: Whether the day represents rest.
        :type is_rest: bool
        :param title: Optional human-readable title.
        :type title: str | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging the row.
        :type flush: bool
        :returns: The staged :class:`RoutineDay` entity.
        :rtype: RoutineDay
        """
        idx = day_index if day_index is not None else self._next_day_index(routine_id)
        row = RoutineDay(
            routine_id=routine_id, day_index=idx, is_rest=is_rest, title=title, notes=notes
        )
        self.session.add(row)
        if flush:
            self.flush()
        return row

    # ---------------------- Day-exercises (ordered) ---------------------------
    def _next_position(self, routine_day_id: int) -> int:
        q = select(func.coalesce(func.max(RoutineDayExercise.position), 0) + 1).where(
            RoutineDayExercise.routine_day_id == routine_day_id
        )
        return int(self.session.execute(q).scalar_one())

    def add_exercise_to_day(
        self,
        routine_day_id: int,
        exercise_id: int,
        *,
        position: int | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> RoutineDayExercise:
        """Attach an exercise to a routine day with positional ordering.

        :param routine_day_id: Identifier of the parent routine day.
        :type routine_day_id: int
        :param exercise_id: Identifier of the exercise to reference.
        :type exercise_id: int
        :param position: Optional explicit position; ``None`` appends at end.
        :type position: int | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging the row.
        :type flush: bool
        :returns: The staged :class:`RoutineDayExercise` row.
        :rtype: RoutineDayExercise
        """
        pos = position if position is not None else self._next_position(routine_day_id)
        row = RoutineDayExercise(
            routine_day_id=routine_day_id,
            exercise_id=exercise_id,
            position=pos,
            notes=notes,
        )
        self.session.add(row)
        if flush:
            self.flush()
        return row

    # ----------------------------- Sets (planned) -----------------------------
    def upsert_set(
        self,
        routine_day_exercise_id: int,
        set_index: int,
        *,
        is_warmup: bool | None = None,
        to_failure: bool | None = None,
        target_weight_kg: float | None = None,
        target_reps: int | None = None,
        target_rir: int | None = None,
        target_rpe: float | None = None,
        target_tempo: str | None = None,
        target_rest_s: int | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> RoutineExerciseSet:
        """Insert or update a planned set identified by its composite key.

        :param routine_day_exercise_id: Identifier of the parent day exercise.
        :type routine_day_exercise_id: int
        :param set_index: Ordinal identifying the set (1-based).
        :type set_index: int
        :param is_warmup: Optional warm-up flag to assign.
        :type is_warmup: bool | None
        :param to_failure: Optional failure flag to assign.
        :type to_failure: bool | None
        :param target_weight_kg: Optional weight prescription in kilograms.
        :type target_weight_kg: float | None
        :param target_reps: Optional target repetitions.
        :type target_reps: int | None
        :param target_rir: Optional target reps-in-reserve.
        :type target_rir: int | None
        :param target_rpe: Optional target RPE.
        :type target_rpe: float | None
        :param target_tempo: Optional tempo notation.
        :type target_tempo: str | None
        :param target_rest_s: Optional rest interval in seconds.
        :type target_rest_s: int | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging changes.
        :type flush: bool
        :returns: The inserted or updated :class:`RoutineExerciseSet` row.
        :rtype: RoutineExerciseSet
        """
        stmt = select(RoutineExerciseSet).where(
            and_(
                RoutineExerciseSet.routine_day_exercise_id == routine_day_exercise_id,
                RoutineExerciseSet.set_index == set_index,
            )
        )
        existing = cast(RoutineExerciseSet | None, self.session.execute(stmt).scalars().first())
        if existing is None:
            row = RoutineExerciseSet(
                routine_day_exercise_id=routine_day_exercise_id, set_index=set_index
            )
            self.session.add(row)
        else:
            row = existing

        # Assign optional fields if provided
        if is_warmup is not None:
            row.is_warmup = is_warmup
        if to_failure is not None:
            row.to_failure = to_failure
        if target_weight_kg is not None:
            row.target_weight_kg = target_weight_kg
        if target_reps is not None:
            row.target_reps = target_reps
        if target_rir is not None:
            row.target_rir = target_rir
        if target_rpe is not None:
            row.target_rpe = target_rpe
        if target_tempo is not None:
            row.target_tempo = target_tempo
        if target_rest_s is not None:
            row.target_rest_s = target_rest_s
        if notes is not None:
            row.notes = notes

        if flush:
            self.flush()
        return row

    # ----------------------------- Pagination ----------------------------------
    def paginate_public(self, pagination: Pagination, *, with_total: bool = True) -> Page[Routine]:
        """Paginate public routines with deterministic ordering.

        :param pagination: Pagination parameters and sort tokens.
        :type pagination: Pagination
        :param with_total: Whether to compute the total row count.
        :type with_total: bool
        :returns: Page containing public routines and metadata.
        :rtype: Page[Routine]
        """
        stmt: Select[Any] = select(self.model).where(self.model.is_public.is_(True))
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), pagination.sort, pk_attr=self._pk_attr()
        )

        items, total = paginate_select(
            self.session, stmt, page=pagination.page, limit=pagination.limit, with_total=with_total
        )
        return Page(
            items=items,
            total=(total if with_total else 0),
            page=pagination.page,
            limit=pagination.limit,
        )


class SubjectRoutineRepository(BaseRepository[SubjectRoutine]):
    """Persist :class:`SubjectRoutine` association rows.

    The repository encapsulates safe persistence helpers for the
    subject-to-routine saved list. Transactions are orchestrated by callers.
    """

    model = SubjectRoutine

    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "routine_id": self.model.routine_id,
            "saved_on": self.model.saved_on,
            "is_active": self.model.is_active,
            "created_at": self.model.created_at,
        }

    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        return {
            "subject_id": self.model.subject_id,
            "routine_id": self.model.routine_id,
            "is_active": self.model.is_active,
        }

    def _updatable_fields(self) -> set[str]:
        return {"is_active"}

    # --------------------------- Association ops ------------------------------
    def save(self, subject_id: int, routine_id: int, *, flush: bool = True) -> SubjectRoutine:
        """Ensure that a subject has a saved routine entry.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param routine_id: Identifier of the routine.
        :type routine_id: int
        :param flush: Whether to flush the session after staging the row.
        :type flush: bool
        :returns: Existing or newly created :class:`SubjectRoutine` row.
        :rtype: SubjectRoutine
        """
        stmt = select(self.model).where(
            and_(self.model.subject_id == subject_id, self.model.routine_id == routine_id)
        )
        existing = cast(SubjectRoutine | None, self.session.execute(stmt).scalars().first())
        if existing is not None:
            return existing
        # SQLite stores the string "false" when relying on the server_default,
        # which SQLAlchemy interprets as truthy when hydrated back. Set the
        # flag explicitly so new links start inactive regardless of backend.
        link = self.model(subject_id=subject_id, routine_id=routine_id, is_active=False)
        self.session.add(link)
        if flush:
            self.flush()
        return link

    def remove(self, subject_id: int, routine_id: int, *, flush: bool = True) -> int:
        """Remove a saved routine link.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param routine_id: Identifier of the routine.
        :type routine_id: int
        :param flush: Whether to flush the session after deletion.
        :type flush: bool
        :returns: Number of rows removed (0 or 1).
        :rtype: int
        """
        stmt = (
            select(self.model)
            .where(and_(self.model.subject_id == subject_id, self.model.routine_id == routine_id))
            .limit(1)
        )
        link = self.session.execute(stmt).scalars().first()
        if not link:
            return 0
        self.session.delete(link)
        if flush:
            self.flush()
        return 1

    def set_active(
        self, subject_id: int, routine_id: int, is_active: bool, *, flush: bool = True
    ) -> SubjectRoutine:
        """Toggle the ``is_active`` flag on a saved routine.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param routine_id: Identifier of the routine.
        :type routine_id: int
        :param is_active: Desired active state.
        :type is_active: bool
        :param flush: Whether to flush the session after mutation.
        :type flush: bool
        :returns: The ensured :class:`SubjectRoutine` row with updated state.
        :rtype: SubjectRoutine
        """
        link = self.save(subject_id, routine_id, flush=False)
        link = cast(SubjectRoutine, link)
        link.is_active = is_active
        if flush:
            self.flush()
        return link

    def list_saved_by_subject(
        self, subject_id: int, *, sort: Iterable[str] | None = None
    ) -> list[SubjectRoutine]:
        """List saved routines for a subject with optional sorting.

        :param subject_id: Identifier of the subject.
        :type subject_id: int
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Saved routine associations ordered deterministically.
        :rtype: list[SubjectRoutine]
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())
