# backend/app/repositories/cycle.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any, cast

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import InstrumentedAttribute

from app.models.cycle import Cycle
from app.repositories import base as base_module
from app.repositories.base import BaseRepository, Page, Pagination, paginate_select


class CycleRepository(BaseRepository[Cycle]):
    """
    Persistence-only repository for :class:`Cycle`.

    - Unicidad por (subject_id, routine_id, cycle_number)
    - Helpers para numeración, arranque y cierre del ciclo
    - Listados por subject/routine y paginación por rangos de fecha
    """

    model = Cycle

    # ----------------------------- Whitelists ---------------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        return {
            "id": self.model.id,
            "subject_id": self.model.subject_id,
            "routine_id": self.model.routine_id,
            "cycle_number": self.model.cycle_number,
            "started_on": self.model.started_on,
            "ended_on": self.model.ended_on,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
        }

    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        return {
            "subject_id": self.model.subject_id,
            "routine_id": self.model.routine_id,
            "cycle_number": self.model.cycle_number,
        }

    def _updatable_fields(self) -> set[str]:
        # Campos mutables de un ciclo existente; no permitimos cambiar PK lógicas.
        return {"started_on", "ended_on", "notes"}

    # ----------------------------- Eager loading ------------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        # Relaciones ya van con lazy="selectin" en el modelo; no forzamos joins aquí.
        return stmt

    # ----------------------------- Lookups ------------------------------------
    def get_by_unique(self, subject_id: int, routine_id: int, cycle_number: int) -> Cycle | None:
        stmt = select(self.model).where(
            and_(
                self.model.subject_id == subject_id,
                self.model.routine_id == routine_id,
                self.model.cycle_number == cycle_number,
            )
        )
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(Cycle | None, result)

    def next_cycle_number(self, subject_id: int, routine_id: int) -> int:
        """Devuelve MAX(cycle_number)+1 para (subject,routine) o 1 si no hay ciclos."""
        q = select(func.coalesce(func.max(self.model.cycle_number), 0) + 1).where(
            and_(self.model.subject_id == subject_id, self.model.routine_id == routine_id)
        )
        return int(self.session.execute(q).scalar_one())

    def ensure_cycle_number(self, cycle: Cycle) -> Cycle:
        """Si `cycle.cycle_number` es None/0, asigna el siguiente número disponible."""
        if not getattr(cycle, "cycle_number", None) or cycle.cycle_number <= 0:
            cycle.cycle_number = self.next_cycle_number(cycle.subject_id, cycle.routine_id)
        return cycle

    # ----------------------------- Mutations ----------------------------------
    def create_cycle(
        self,
        *,
        subject_id: int,
        routine_id: int,
        cycle_number: int | None = None,
        started_on: date | None = None,
        ended_on: date | None = None,
        notes: str | None = None,
        flush: bool = True,
    ) -> Cycle:
        """Crea un ciclo; si no se pasa `cycle_number`, se autoincrementa por (subject,routine)."""
        if cycle_number is None or not cycle_number or cycle_number <= 0:
            cycle_number = self.next_cycle_number(subject_id, routine_id)

        row = self.model(
            subject_id=subject_id,
            routine_id=routine_id,
            cycle_number=int(cycle_number),
            started_on=started_on,
            ended_on=ended_on,
            notes=notes,
        )
        self.session.add(row)
        if flush:
            self.flush()
        return row

    def start_cycle(self, cycle_id: int, started_on: date) -> Cycle:
        """Marca `started_on` (no toca ended_on)."""
        row = self.get(cycle_id)
        if not row:
            raise ValueError(f"Cycle {cycle_id} not found.")
        self.assign_updates(row, {"started_on": started_on})
        return row

    def finish_cycle(self, cycle_id: int, ended_on: date) -> Cycle:
        """Marca `ended_on` (no toca started_on)."""
        row = self.get(cycle_id)
        if not row:
            raise ValueError(f"Cycle {cycle_id} not found.")
        self.assign_updates(row, {"ended_on": ended_on})
        return row

    # ----------------------------- Listings -----------------------------------
    def list_by_subject(
        self,
        subject_id: int,
        *,
        sort: Iterable[str] | None = None,
    ) -> list[Cycle]:
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_routine(
        self,
        routine_id: int,
        *,
        sort: Iterable[str] | None = None,
    ) -> list[Cycle]:
        stmt: Select[Any] = select(self.model).where(self.model.routine_id == routine_id)
        stmt = self._default_eagerload(stmt)
        stmt = base_module._apply_sorting(
            stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr()
        )
        return list(self.session.execute(stmt).scalars().all())

    def paginate_for_subject(
        self,
        pagination: Pagination,
        *,
        subject_id: int,
        routine_id: int | None = None,
        with_total: bool = True,
    ) -> Page[Cycle]:
        """
        Pagina ciclos de un subject, opcionalmente filtrando por routine.
        """
        stmt: Select[Any] = select(self.model).where(self.model.subject_id == subject_id)
        if routine_id is not None:
            stmt = stmt.where(self.model.routine_id == routine_id)

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
