from __future__ import annotations

import logging

from app.repositories.routine import RoutineRepository
from app.services._shared.base import BaseService
from app.services._shared.dto import PageMeta
from app.services._shared.errors import NotFoundError

from ._converters import routine_to_out
from .dto import (
    RoutineGetIn,
    RoutineListOut,
    RoutineOwnerListIn,
    RoutineOwnerListOut,
    RoutineOut,
    RoutinePublicListIn,
)

logger = logging.getLogger(__name__)


class RoutineQueryService(BaseService):
    """Read-only routines service exposing aggregate projections."""

    def get(self, dto: RoutineGetIn) -> RoutineOut:
        """Retrieve a routine ensuring access control."""

        with self.ro_uow() as uow:
            repo: RoutineRepository = uow.routines
            routine = repo.get(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            if not routine.is_public:
                self.ensure_owner(
                    actor_id=self.ctx.subject_id,
                    owner_id=routine.owner_subject_id,
                    msg="Only the owner can access this routine.",
                )

            logger.info("Routine fetched", extra={"routine_id": routine.id, "actor": self.ctx.subject_id})
            return routine_to_out(routine)

    def list_by_owner(self, dto: RoutineOwnerListIn) -> RoutineOwnerListOut:
        """List all routines owned by a subject applying optional sorting."""

        self.ensure_owner(
            actor_id=self.ctx.subject_id,
            owner_id=dto.owner_subject_id,
            msg="Cannot list routines for another subject.",
        )

        with self.ro_uow() as uow:
            repo: RoutineRepository = uow.routines
            rows = repo.list_by_owner(dto.owner_subject_id, sort=dto.sort)
            logger.info(
                "Listed routines for owner",
                extra={"owner_subject_id": dto.owner_subject_id, "count": len(rows)},
            )
            return RoutineOwnerListOut(items=[routine_to_out(row) for row in rows])

    def paginate_public(self, dto: RoutinePublicListIn) -> RoutineListOut:
        """Paginate public routines with deterministic ordering."""

        pagination = self.ensure_pagination(
            page=dto.pagination.page, limit=dto.pagination.limit, sort=dto.pagination.sort
        )

        with self.ro_uow() as uow:
            repo: RoutineRepository = uow.routines
            page = repo.paginate_public(pagination, with_total=dto.with_total)
            items = list(page.items)
            logger.info(
                "Paginated public routines",
                extra={"page": page.page, "limit": page.limit, "returned": len(items)},
            )
            has_next = (
                (page.page * page.limit) < page.total if dto.with_total else len(items) >= page.limit
            )
            meta = PageMeta(
                page=page.page,
                limit=page.limit,
                total=page.total,
                has_prev=page.page > 1,
                has_next=has_next,
            )
            return RoutineListOut(items=[routine_to_out(row) for row in items], meta=meta)
