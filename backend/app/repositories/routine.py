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
    """
    Persistence-only repository for :class:`Routine` (aggregate root).
    Provides helpers to manage child rows (days, day-exercises, sets).
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
        """
        Load the full plan efficiently (selectin on collections).
        """
        return stmt.options(
            selectinload(self.model.days)
            .selectinload(RoutineDay.exercises)
            .selectinload(RoutineDayExercise.sets)
        )

    # ----------------------------- Lookups ------------------------------------
    def get_by_owner_and_name(self, owner_subject_id: int, name: str) -> Routine | None:
        stmt: Select[Any] = select(self.model).where(
            and_(self.model.owner_subject_id == owner_subject_id, self.model.name == name)
        )
        stmt = self._default_eagerload(stmt)
        return cast(Routine | None, self.session.execute(stmt).scalars().first())

    def list_by_owner(
        self, owner_subject_id: int, *, sort: Iterable[str] | None = None
    ) -> list[Routine]:
        stmt: Select[Any] = select(self.model).where(
            self.model.owner_subject_id == owner_subject_id
        )
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_public(self, *, sort: Iterable[str] | None = None) -> list[Routine]:
        stmt: Select[Any] = select(self.model).where(self.model.is_public.is_(True))
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    # ----------------------------- Days ---------------------------------------
    def _next_day_index(self, routine_id: int) -> int:
        """Return the next available day_index for a routine."""
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
        """
        Create a day row. If ``day_index`` is None, append at the end.
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
        """
        Add an exercise to a day at the given position. If None, append.
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
        """
        Insert or update a planned set identified by (routine_day_exercise_id, set_index).
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
    """
    Persistence-only repository for :class:`SubjectRoutine` association.
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
        """
        Idempotently ensure a SubjectRoutine exists (saved).
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
        """
        Remove saved routine link. Returns number of rows removed (0/1).
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
        """
        Toggle active flag for a subject-routine association.
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
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())
