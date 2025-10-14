from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.services._shared.dto import PageMeta, PaginationIn


# ------------------------------ Output DTOs ------------------------------ #


@dataclass(frozen=True, slots=True)
class RoutineExerciseSetOut:
    """Public projection of a planned set within a routine day exercise."""

    id: int
    set_index: int
    is_warmup: bool
    to_failure: bool
    target_weight_kg: float | None
    target_reps: int | None
    target_rir: int | None
    target_rpe: float | None
    target_tempo: str | None
    target_rest_s: int | None
    notes: str | None
    created_at: object
    updated_at: object


@dataclass(frozen=True, slots=True)
class RoutineDayExerciseOut:
    """Exercise scheduled for a specific routine day with ordered sets."""

    id: int
    routine_day_id: int
    exercise_id: int
    position: int
    notes: str | None
    created_at: object
    updated_at: object
    sets: list[RoutineExerciseSetOut]


@dataclass(frozen=True, slots=True)
class RoutineDayOut:
    """Day within a routine cycle including ordered exercises."""

    id: int
    routine_id: int
    day_index: int
    is_rest: bool
    title: str | None
    notes: str | None
    created_at: object
    updated_at: object
    exercises: list[RoutineDayExerciseOut]


@dataclass(frozen=True, slots=True)
class RoutineOut:
    """Routine aggregate with nested days, exercises and sets eagerly loaded."""

    id: int
    owner_subject_id: int
    name: str
    description: str | None
    is_public: bool
    created_at: object
    updated_at: object
    days: list[RoutineDayOut]


@dataclass(frozen=True, slots=True)
class RoutineListOut:
    """Paginated listing of routines with metadata."""

    items: list[RoutineOut]
    meta: PageMeta


@dataclass(frozen=True, slots=True)
class RoutineOwnerListOut:
    """Non-paginated listing of routines owned by a subject."""

    items: list[RoutineOut]


@dataclass(frozen=True, slots=True)
class SubjectRoutineOut:
    """Projection of a subject saved routine link."""

    id: int
    subject_id: int
    routine_id: int
    is_active: bool
    saved_on: object
    created_at: object
    updated_at: object


@dataclass(frozen=True, slots=True)
class SubjectRoutineListOut:
    """Collection of saved routines for a subject."""

    items: list[SubjectRoutineOut]


@dataclass(frozen=True, slots=True)
class SubjectRoutineRemoveOut:
    """Result of removing a saved routine link."""

    removed: int


# ------------------------------ Input DTOs ------------------------------- #


@dataclass(frozen=True, slots=True)
class RoutineGetIn:
    """Retrieve a routine by its identifier."""

    routine_id: int


@dataclass(frozen=True, slots=True)
class RoutineCreateIn:
    """Create a new routine aggregate for the given owner."""

    owner_subject_id: int
    name: str
    description: str | None = None
    is_public: bool = False
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class RoutineUpdateIn:
    """Update mutable fields on a routine aggregate."""

    routine_id: int
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


@dataclass(frozen=True, slots=True)
class RoutineDeleteIn:
    """Delete a routine aggregate."""

    routine_id: int


@dataclass(frozen=True, slots=True)
class RoutineDayCreateIn:
    """Create or append a day within a routine."""

    routine_id: int
    day_index: int | None = None
    is_rest: bool = False
    title: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class RoutineDayExerciseAddIn:
    """Attach an exercise to a routine day."""

    routine_day_id: int
    exercise_id: int
    position: int | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class RoutineSetUpsertIn:
    """Insert or update a planned set for a routine day exercise."""

    routine_day_exercise_id: int
    set_index: int
    is_warmup: bool | None = None
    to_failure: bool | None = None
    target_weight_kg: float | None = None
    target_reps: int | None = None
    target_rir: int | None = None
    target_rpe: float | None = None
    target_tempo: str | None = None
    target_rest_s: int | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class RoutineOwnerListIn:
    """List routines owned by a subject."""

    owner_subject_id: int
    sort: Iterable[str] | None = None


@dataclass(frozen=True, slots=True)
class RoutinePublicListIn:
    """Paginate over public routines."""

    pagination: PaginationIn
    with_total: bool = True


@dataclass(frozen=True, slots=True)
class RoutinePublishIn:
    """Toggle routine public visibility."""

    routine_id: int
    make_public: bool


@dataclass(frozen=True, slots=True)
class SubjectRoutineSaveIn:
    """Ensure a subject has a saved routine entry."""

    subject_id: int
    routine_id: int


@dataclass(frozen=True, slots=True)
class SubjectRoutineRemoveIn:
    """Remove a saved routine entry."""

    subject_id: int
    routine_id: int


@dataclass(frozen=True, slots=True)
class SubjectRoutineActivateIn:
    """Toggle the active flag on a saved routine."""

    subject_id: int
    routine_id: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class SubjectRoutineListIn:
    """List saved routines for a subject."""

    subject_id: int
    sort: Iterable[str] | None = None
