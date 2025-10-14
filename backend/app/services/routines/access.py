from __future__ import annotations

import logging

from app.repositories.routine import RoutineRepository, SubjectRoutineRepository
from app.services._shared.base import BaseService
from app.services._shared.errors import AuthorizationError, NotFoundError

from ._converters import subject_routine_to_out
from .dto import (
    SubjectRoutineActivateIn,
    SubjectRoutineListIn,
    SubjectRoutineListOut,
    SubjectRoutineOut,
    SubjectRoutineRemoveIn,
    SubjectRoutineRemoveOut,
    SubjectRoutineSaveIn,
)

logger = logging.getLogger(__name__)


class RoutineAccessService(BaseService):
    """Manage subject access to routines (save/activate/remove/list)."""

    def save(self, dto: SubjectRoutineSaveIn) -> SubjectRoutineOut:
        """Save a routine for a subject after authorization checks."""

        self.ensure_owner(
            actor_id=self.ctx.subject_id,
            owner_id=dto.subject_id,
            msg="Cannot save routines for another subject.",
        )

        with self.rw_uow() as uow:
            routines_repo: RoutineRepository = uow.routines
            subject_repo: SubjectRoutineRepository = uow.subject_routines

            routine = routines_repo.get(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            if routine.owner_subject_id != dto.subject_id and not routine.is_public:
                raise AuthorizationError("Routine is private and not owned by subject.")

            link = subject_repo.save(dto.subject_id, dto.routine_id)
            logger.info(
                "Routine saved for subject",
                extra={"subject_id": dto.subject_id, "routine_id": dto.routine_id},
            )
            return subject_routine_to_out(link)

    def remove(self, dto: SubjectRoutineRemoveIn) -> SubjectRoutineRemoveOut:
        """Remove a saved routine link (idempotent)."""

        self.ensure_owner(
            actor_id=self.ctx.subject_id,
            owner_id=dto.subject_id,
            msg="Cannot remove routines for another subject.",
        )

        with self.rw_uow() as uow:
            repo: SubjectRoutineRepository = uow.subject_routines
            removed = repo.remove(dto.subject_id, dto.routine_id)
            logger.info(
                "Routine removed for subject",
                extra={"subject_id": dto.subject_id, "routine_id": dto.routine_id, "removed": removed},
            )
            return SubjectRoutineRemoveOut(removed=removed)

    def set_active(self, dto: SubjectRoutineActivateIn) -> SubjectRoutineOut:
        """Activate or deactivate a saved routine for the subject."""

        self.ensure_owner(
            actor_id=self.ctx.subject_id,
            owner_id=dto.subject_id,
            msg="Cannot modify active routine for another subject.",
        )

        with self.rw_uow() as uow:
            routines_repo: RoutineRepository = uow.routines
            subject_repo: SubjectRoutineRepository = uow.subject_routines

            routine = routines_repo.get(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            if routine.owner_subject_id != dto.subject_id and not routine.is_public:
                raise AuthorizationError("Routine is private and not owned by subject.")

            link = subject_repo.set_active(dto.subject_id, dto.routine_id, dto.is_active)
            logger.info(
                "Routine active flag updated",
                extra={
                    "subject_id": dto.subject_id,
                    "routine_id": dto.routine_id,
                    "is_active": link.is_active,
                },
            )
            return subject_routine_to_out(link)

    def list_saved(self, dto: SubjectRoutineListIn) -> SubjectRoutineListOut:
        """List saved routines for the authenticated subject."""

        self.ensure_owner(
            actor_id=self.ctx.subject_id,
            owner_id=dto.subject_id,
            msg="Cannot list saved routines for another subject.",
        )

        with self.ro_uow() as uow:
            repo: SubjectRoutineRepository = uow.subject_routines
            rows = repo.list_saved_by_subject(dto.subject_id, sort=dto.sort)
            logger.info(
                "Listed saved routines",
                extra={"subject_id": dto.subject_id, "count": len(rows)},
            )
            return SubjectRoutineListOut(items=[subject_routine_to_out(row) for row in rows])
