from __future__ import annotations

import logging

from app.models.routine import Routine
from app.repositories.routine import RoutineRepository
from app.services._shared.base import BaseService
from app.services._shared.errors import NotFoundError, PreconditionFailedError

from ._converters import routine_to_out
from .dto import RoutineOut, RoutinePublishIn

logger = logging.getLogger(__name__)


def _is_publishable(routine: Routine) -> bool:
    """Routine must contain at least one day with at least one exercise."""

    if not routine.days:
        return False
    return any(day.exercises for day in routine.days)


class RoutinePublishingService(BaseService):
    """Handle public visibility transitions for routines."""

    def set_public(self, dto: RoutinePublishIn) -> RoutineOut:
        """Toggle routine visibility enforcing structural checks."""

        with self.rw_uow() as uow:
            repo: RoutineRepository = uow.routines
            routine = repo.get_for_update(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            self.ensure_owner(
                actor_id=self.ctx.subject_id,
                owner_id=routine.owner_subject_id,
                msg="Cannot change visibility of another subject's routine.",
            )

            if dto.make_public and not _is_publishable(routine):
                raise PreconditionFailedError(
                    "Routine must include at least one day with exercises before publishing."
                )

            if routine.is_public == dto.make_public:
                logger.info(
                    "Routine publish request was idempotent",
                    extra={"routine_id": routine.id, "is_public": routine.is_public},
                )
                return routine_to_out(routine)

            repo.assign_updates(routine, {"is_public": dto.make_public})
            logger.info(
                "Routine visibility updated",
                extra={"routine_id": routine.id, "is_public": dto.make_public},
            )
            return routine_to_out(routine)
