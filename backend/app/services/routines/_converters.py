from __future__ import annotations

from operator import attrgetter

from operator import attrgetter

from app.models.routine import Routine, RoutineDay, RoutineDayExercise, RoutineExerciseSet, SubjectRoutine

from .dto import (
    RoutineDayExerciseOut,
    RoutineDayOut,
    RoutineExerciseSetOut,
    RoutineOut,
    SubjectRoutineOut,
)


def _set_to_out(row: RoutineExerciseSet) -> RoutineExerciseSetOut:
    return RoutineExerciseSetOut(
        id=row.id,
        set_index=row.set_index,
        is_warmup=row.is_warmup,
        to_failure=row.to_failure,
        target_weight_kg=row.target_weight_kg,
        target_reps=row.target_reps,
        target_rir=row.target_rir,
        target_rpe=row.target_rpe,
        target_tempo=row.target_tempo,
        target_rest_s=row.target_rest_s,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def routine_set_to_out(row: RoutineExerciseSet) -> RoutineExerciseSetOut:
    """Public helper for converting a routine set to its DTO."""

    return _set_to_out(row)


def routine_day_exercise_to_out(row: RoutineDayExercise) -> RoutineDayExerciseOut:
    sets = sorted(row.sets, key=attrgetter("set_index", "id"))
    return RoutineDayExerciseOut(
        id=row.id,
        routine_day_id=row.routine_day_id,
        exercise_id=row.exercise_id,
        position=row.position,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sets=[_set_to_out(s) for s in sets],
    )


def routine_day_to_out(row: RoutineDay) -> RoutineDayOut:
    exercises = sorted(row.exercises, key=attrgetter("position", "id"))
    return RoutineDayOut(
        id=row.id,
        routine_id=row.routine_id,
        day_index=row.day_index,
        is_rest=row.is_rest,
        title=row.title,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        exercises=[routine_day_exercise_to_out(ex) for ex in exercises],
    )


def routine_to_out(row: Routine) -> RoutineOut:
    days = sorted(row.days, key=attrgetter("day_index", "id"))
    return RoutineOut(
        id=row.id,
        owner_subject_id=row.owner_subject_id,
        name=row.name,
        description=row.description,
        is_public=row.is_public,
        created_at=row.created_at,
        updated_at=row.updated_at,
        days=[routine_day_to_out(day) for day in days],
    )


def subject_routine_to_out(row: SubjectRoutine) -> SubjectRoutineOut:
    return SubjectRoutineOut(
        id=row.id,
        subject_id=row.subject_id,
        routine_id=row.routine_id,
        is_active=row.is_active,
        saved_on=row.saved_on,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
