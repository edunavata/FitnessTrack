# backend/app/repositories/workout.py
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
    """
    Persistence-only repository for :class:`WorkoutSession`.

    Clave única: (subject_id, workout_date).
    Incluye consultas por sujeto + rango de fechas, por ciclo, y utilidades de estado.
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
        # Campos mutables. No permitimos cambiar subject_id ni workout_date (clave lógica).
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
        # El modelo ya usa lazy="selectin" en relaciones; mantener liviano.
        return stmt

    # ---------------------------- Lookups ----------------------------
    def get_by_unique(self, subject_id: int, workout_date: datetime) -> WorkoutSession | None:
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
        """
        Crea una sesión nueva. Valida automáticamente el ciclo vía @validates del modelo.
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
        """
        Inserta o actualiza por la clave única (subject_id, workout_date).
        Las claves lógicas no cambian; solo asigna campos no-None.
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
        """
        Asocia/desasocia una sesión a un ciclo. Valida subject_id vía @validates.
        """
        row = self.get(ws_id)
        if not row:
            raise ValueError(f"WorkoutSession {ws_id} not found.")
        self.assign_updates(row, {"cycle_id": cycle_id}, strict=True, flush=flush)
        return row

    def mark_completed(self, ws_id: int, *, flush: bool = True) -> WorkoutSession:
        """Marca la sesión como COMPLETED."""
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
        """
        Lista sesiones por sujeto y rango de fechas (workout_date, inclusive).
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
        """
        Pagina sesiones por sujeto (rango de fechas opcional).
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
        """
        Lista sesiones que pertenecen a un ciclo.
        """
        stmt: Select[Any] = select(self.model).where(self.model.cycle_id == cycle_id)
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())
