"""Cycle repository implementing persistence-focused operations.

This module houses the :class:`CycleRepository`, a thin wrapper around the
generic :class:`~app.repositories.base.BaseRepository` that is responsible for
CRUD access to :class:`app.models.cycle.Cycle`. All helpers stay within the
persistence boundary — there is no business logic or transaction management
here; services own the Unit of Work.
"""

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
    """Persist ``Cycle`` aggregates and expose persistence-oriented helpers.

    The repository guarantees deterministic pagination by applying the
    whitelisted sorting options defined in :meth:`_sortable_fields` and keeps
    cycle numbering consistent with the unique key
    ``(subject_id, routine_id, cycle_number)``. Transactions are managed by the
    calling service layer; this class only interacts with the active session.
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
        # Mutable fields for an existing cycle; logical keys remain immutable.
        return {"started_on", "ended_on", "notes"}

    # ----------------------------- Eager loading ------------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        # Relationships already use selectin loading at the model level; no joins needed.
        return stmt

    # ----------------------------- Lookups ------------------------------------
    def get_by_unique(self, subject_id: int, routine_id: int, cycle_number: int) -> Cycle | None:
        """Return a cycle identified by its composite unique key.

        :param subject_id: Identifier of the owning subject.
        :type subject_id: int
        :param routine_id: Identifier of the related routine.
        :type routine_id: int
        :param cycle_number: Sequential number within the routine/subject pair.
        :type cycle_number: int
        :returns: The matching cycle or ``None`` when absent.
        :rtype: Cycle | None
        """
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
        """Compute the next sequential cycle number for the pair.

        :param subject_id: Identifier of the owning subject.
        :type subject_id: int
        :param routine_id: Identifier of the related routine.
        :type routine_id: int
        :returns: The next available ``cycle_number`` starting at ``1``.
        :rtype: int
        """
        q = select(func.coalesce(func.max(self.model.cycle_number), 0) + 1).where(
            and_(self.model.subject_id == subject_id, self.model.routine_id == routine_id)
        )
        return int(self.session.execute(q).scalar_one())

    def ensure_cycle_number(self, cycle: Cycle) -> Cycle:
        """Ensure a cycle has a positive ``cycle_number`` assigned.

        The helper mutates the provided instance in-place. When the number is
        unset or zero, the repository queries :meth:`next_cycle_number` to keep
        numbering unique per ``(subject_id, routine_id)``.

        :param cycle: Cycle instance to normalise.
        :type cycle: Cycle
        :returns: The same instance with a guaranteed ``cycle_number``.
        :rtype: Cycle
        """
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
        """Create and stage a ``Cycle`` row for persistence.

        When ``cycle_number`` is omitted the method assigns the next available
        number per ``(subject_id, routine_id)`` to honour the uniqueness
        constraint enforced at the database level.

        :param subject_id: Identifier of the owning subject.
        :type subject_id: int
        :param routine_id: Identifier of the related routine.
        :type routine_id: int
        :param cycle_number: Optional explicit sequential number.
        :type cycle_number: int | None
        :param started_on: Optional start date of the training cycle.
        :type started_on: datetime.date | None
        :param ended_on: Optional end date of the training cycle.
        :type ended_on: datetime.date | None
        :param notes: Optional free-form notes.
        :type notes: str | None
        :param flush: Whether to flush the session after staging the entity.
        :type flush: bool
        :returns: The staged cycle entity.
        :rtype: Cycle
        """
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
        """Set the ``started_on`` date for a persisted cycle.

        :param cycle_id: Identifier of the cycle to mutate.
        :type cycle_id: int
        :param started_on: Date marking the cycle start.
        :type started_on: datetime.date
        :returns: The mutated cycle instance.
        :rtype: Cycle
        :raises ValueError: If the cycle cannot be found.
        """
        row = self.get(cycle_id)
        if not row:
            raise ValueError(f"Cycle {cycle_id} not found.")
        self.assign_updates(row, {"started_on": started_on})
        return row

    def finish_cycle(self, cycle_id: int, ended_on: date) -> Cycle:
        """Set the ``ended_on`` date for a persisted cycle.

        :param cycle_id: Identifier of the cycle to mutate.
        :type cycle_id: int
        :param ended_on: Date marking the cycle end.
        :type ended_on: datetime.date
        :returns: The mutated cycle instance.
        :rtype: Cycle
        :raises ValueError: If the cycle cannot be found.
        """
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
        """List cycles owned by a subject with optional sorting.

        :param subject_id: Identifier of the owning subject.
        :type subject_id: int
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Ordered list of cycles.
        :rtype: list[Cycle]
        """
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
        """List cycles associated with a specific routine.

        :param routine_id: Identifier of the related routine.
        :type routine_id: int
        :param sort: Public sort tokens processed through the whitelist.
        :type sort: Iterable[str] | None
        :returns: Ordered list of cycles.
        :rtype: list[Cycle]
        """
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
        """Paginate cycles for a subject with an optional routine filter.

        :param pagination: Pagination parameters and sort tokens.
        :type pagination: Pagination
        :param subject_id: Identifier of the owning subject.
        :type subject_id: int
        :param routine_id: Optional routine to scope the listing.
        :type routine_id: int | None
        :param with_total: Whether to compute the total row count.
        :type with_total: bool
        :returns: Page of cycles respecting deterministic ordering.
        :rtype: Page[Cycle]
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
