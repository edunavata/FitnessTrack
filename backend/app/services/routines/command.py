from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError

from app.models.routine import RoutineDay, RoutineDayExercise
from app.repositories.routine import RoutineRepository
from app.services._shared.base import BaseService
from app.services._shared.errors import ConflictError, NotFoundError

from ._converters import (
    routine_day_exercise_to_out,
    routine_day_to_out,
    routine_set_to_out,
    routine_to_out,
)
from .dto import (
    RoutineCreateIn,
    RoutineDayCreateIn,
    RoutineDayExerciseAddIn,
    RoutineDayOut,
    RoutineDayExerciseOut,
    RoutineDeleteIn,
    RoutineExerciseSetOut,
    RoutineOut,
    RoutineSetUpsertIn,
    RoutineUpdateIn,
)

logger = logging.getLogger(__name__)


class RoutineCommandService(BaseService):
    """Orchestrate routine mutations enforcing ownership and consistency."""

    def create(self, dto: RoutineCreateIn) -> RoutineOut:
        """Create a routine ensuring unique name per owner and idempotency."""

        self.ensure_owner(
            actor_id=self.ctx.subject_id,
            owner_id=dto.owner_subject_id,
            msg="Cannot create routines for another subject.",
        )

        def _create() -> RoutineOut:
            with self.rw_uow() as uow:
                repo: RoutineRepository = uow.routines
                existing = repo.get_by_owner_and_name(dto.owner_subject_id, dto.name)
                if existing is not None:
                    if dto.idempotency_key:
                        logger.info(
                            "Idempotent routine create returning existing",
                            extra={"routine_id": existing.id, "owner_subject_id": dto.owner_subject_id},
                        )
                        return routine_to_out(existing)
                    raise ConflictError("Routine", "name already exists for owner")

                routine = repo.model(
                    owner_subject_id=dto.owner_subject_id,
                    name=dto.name,
                    description=dto.description,
                    is_public=dto.is_public,
                )
                repo.add(routine)
                logger.info(
                    "Routine created",
                    extra={"routine_id": routine.id, "owner_subject_id": dto.owner_subject_id},
                )
                return routine_to_out(routine)

        return self.with_idempotency(dto.idempotency_key, _create)

    def update(self, dto: RoutineUpdateIn) -> RoutineOut:
        """Update mutable routine fields after locking the aggregate."""

        with self.rw_uow() as uow:
            repo: RoutineRepository = uow.routines
            routine = repo.get_for_update(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            self.ensure_owner(
                actor_id=self.ctx.subject_id,
                owner_id=routine.owner_subject_id,
                msg="Cannot modify another subject's routine.",
            )

            updates: dict[str, object] = {}
            if dto.name is not None:
                updates["name"] = dto.name
            if dto.description is not None:
                updates["description"] = dto.description
            if dto.is_public is not None:
                updates["is_public"] = dto.is_public

            if updates:
                try:
                    repo.assign_updates(routine, updates)
                except IntegrityError as exc:  # unique owner+name collision
                    raise ConflictError("Routine", "name already exists for owner") from exc

            logger.info("Routine updated", extra={"routine_id": routine.id, "fields": list(updates)})
            return routine_to_out(routine)

    def delete(self, dto: RoutineDeleteIn) -> None:
        """Delete a routine after verifying ownership."""

        with self.rw_uow() as uow:
            repo: RoutineRepository = uow.routines
            routine = repo.get_for_update(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            self.ensure_owner(
                actor_id=self.ctx.subject_id,
                owner_id=routine.owner_subject_id,
                msg="Cannot delete another subject's routine.",
            )

            repo.delete(routine)
            logger.info("Routine deleted", extra={"routine_id": dto.routine_id})

    def add_day(self, dto: RoutineDayCreateIn) -> RoutineDayOut:
        """Append or insert a day into a routine."""

        with self.rw_uow() as uow:
            repo: RoutineRepository = uow.routines
            routine = repo.get_for_update(dto.routine_id)
            if routine is None:
                raise NotFoundError("Routine", dto.routine_id)

            self.ensure_owner(
                actor_id=self.ctx.subject_id,
                owner_id=routine.owner_subject_id,
                msg="Cannot mutate days of another subject's routine.",
            )

            day = repo.add_day(
                dto.routine_id,
                day_index=dto.day_index,
                is_rest=dto.is_rest,
                title=dto.title,
                notes=dto.notes,
            )
            logger.info("Routine day created", extra={"routine_id": dto.routine_id, "day_id": day.id})
            return routine_day_to_out(day)

    def add_day_exercise(self, dto: RoutineDayExerciseAddIn) -> RoutineDayExerciseOut:
        """Attach an exercise to a routine day respecting ordering."""

        with self.rw_uow() as uow:
            repo: RoutineRepository = uow.routines
            day = uow.session.get(RoutineDay, dto.routine_day_id)
            if day is None:
                raise NotFoundError("RoutineDay", dto.routine_day_id)

            # Load routine for auth check
            routine = day.routine
            self.ensure_owner(
                actor_id=self.ctx.subject_id,
                owner_id=routine.owner_subject_id,
                msg="Cannot add exercises to another subject's routine.",
            )

            exercise = repo.add_exercise_to_day(
                dto.routine_day_id,
                dto.exercise_id,
                position=dto.position,
                notes=dto.notes,
            )
            logger.info(
                "Routine day exercise added",
                extra={"routine_day_id": dto.routine_day_id, "exercise_id": exercise.id},
            )
            return routine_day_exercise_to_out(exercise)

    def upsert_set(self, dto: RoutineSetUpsertIn) -> RoutineExerciseSetOut:
        """Insert or update a planned set on a routine day exercise."""

        with self.rw_uow() as uow:
            repo: RoutineRepository = uow.routines
            day_exercise = uow.session.get(RoutineDayExercise, dto.routine_day_exercise_id)
            if day_exercise is None:
                raise NotFoundError("RoutineDayExercise", dto.routine_day_exercise_id)

            routine = day_exercise.routine_day.routine
            self.ensure_owner(
                actor_id=self.ctx.subject_id,
                owner_id=routine.owner_subject_id,
                msg="Cannot edit sets of another subject's routine.",
            )

            set_row = repo.upsert_set(
                dto.routine_day_exercise_id,
                dto.set_index,
                is_warmup=dto.is_warmup,
                to_failure=dto.to_failure,
                target_weight_kg=dto.target_weight_kg,
                target_reps=dto.target_reps,
                target_rir=dto.target_rir,
                target_rpe=dto.target_rpe,
                target_tempo=dto.target_tempo,
                target_rest_s=dto.target_rest_s,
                notes=dto.notes,
            )
            logger.info(
                "Routine set upserted",
                extra={
                    "routine_day_exercise_id": dto.routine_day_exercise_id,
                    "set_index": dto.set_index,
                },
            )
            return routine_set_to_out(set_row)
