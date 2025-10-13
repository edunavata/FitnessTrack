# comments in English; strict reST docstrings
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.services._shared.dto import PageMeta, PaginationIn

# ------------------------------ Output DTOs ------------------------------ #


@dataclass(frozen=True, slots=True)
class ExerciseRowOut:
    """
    Public projection of an Exercise row.

    :param id: Primary key.
    :type id: int
    :param name: Display name.
    :type name: str
    :param slug: Stable unique slug.
    :type slug: str
    :param primary_muscle: Primary muscle enum value.
    :type primary_muscle: str
    :param movement: Movement pattern enum value.
    :type movement: str
    :param mechanics: Mechanics enum value.
    :type mechanics: str
    :param force: Force vector enum value.
    :type force: str
    :param unilateral: Whether the exercise is unilateral.
    :type unilateral: bool
    :param equipment: Equipment enum value.
    :type equipment: str
    :param grip: Optional grip text.
    :type grip: str | None
    :param range_of_motion: Optional ROM description.
    :type range_of_motion: str | None
    :param difficulty: Level enum value.
    :type difficulty: str
    :param cues: Optional coaching cues.
    :type cues: str | None
    :param instructions: Optional how-to text.
    :type instructions: str | None
    :param video_url: Optional demo URL.
    :type video_url: str | None
    :param is_active: Whether the exercise is active in catalog.
    :type is_active: bool
    :param aliases: Alternative names.
    :type aliases: list[str]
    :param tags: Associated tag names.
    :type tags: list[str]
    :param secondary_muscles: Secondary muscle identifiers.
    :type secondary_muscles: list[str]
    :param created_at: Creation timestamp.
    :type created_at: object
    :param updated_at: Update timestamp.
    :type updated_at: object
    """

    id: int
    name: str
    slug: str
    primary_muscle: str
    movement: str
    mechanics: str
    force: str
    unilateral: bool
    equipment: str
    grip: str | None
    range_of_motion: str | None
    difficulty: str
    cues: str | None
    instructions: str | None
    video_url: str | None
    is_active: bool
    aliases: list[str]
    tags: list[str]
    secondary_muscles: list[str]
    created_at: object
    updated_at: object


@dataclass(frozen=True, slots=True)
class ExerciseListOut:
    """
    Paginated list of exercises.

    :param items: List of exercise rows.
    :type items: list[:class:`ExerciseRowOut`]
    :param meta: Pagination metadata.
    :type meta: :class:`PageMeta`
    """

    items: list[ExerciseRowOut]
    meta: PageMeta


@dataclass(frozen=True, slots=True)
class ListByTagOut:
    """
    List of exercises filtered by tag.

    :param items: Matching exercise rows.
    :type items: list[:class:`ExerciseRowOut`]
    """

    items: list[ExerciseRowOut]


@dataclass(frozen=True, slots=True)
class ListBySecondaryOut:
    """
    List of exercises filtered by secondary muscle.

    :param items: Matching exercise rows.
    :type items: list[:class:`ExerciseRowOut`]
    """

    items: list[ExerciseRowOut]


@dataclass(frozen=True, slots=True)
class AliasesOut:
    """
    Normalized alias list.

    :param aliases: Current aliases (sorted).
    :type aliases: list[str]
    """

    aliases: list[str]


@dataclass(frozen=True, slots=True)
class TagsOut:
    """
    Normalized tag list.

    :param tags: Current tags (sorted).
    :type tags: list[str]
    """

    tags: list[str]


@dataclass(frozen=True, slots=True)
class SecondaryOut:
    """
    Normalized secondary muscle list.

    :param secondary_muscles: Current secondary muscles (sorted).
    :type secondary_muscles: list[str]
    """

    secondary_muscles: list[str]


@dataclass(frozen=True, slots=True)
class RemoveCountOut:
    """
    Removal result.

    :param removed: Number of removed records/items.
    :type removed: int
    """

    removed: int


# ------------------------------ Input DTOs ------------------------------- #


@dataclass(frozen=True, slots=True)
class ExerciseCreateIn:
    """
    Exercise creation contract.

    Optional relationship sets are applied atomically with the insert.

    :param name: Exercise display name.
    :type name: str
    :param slug: Unique slug.
    :type slug: str
    :param primary_muscle: Enum value.
    :type primary_muscle: str
    :param movement: Enum value.
    :type movement: str
    :param mechanics: Enum value.
    :type mechanics: str
    :param force: Enum value.
    :type force: str
    :param unilateral: Whether unilateral.
    :type unilateral: bool
    :param equipment: Enum value.
    :type equipment: str
    :param grip: Optional text.
    :type grip: str | None
    :param range_of_motion: Optional text.
    :type range_of_motion: str | None
    :param difficulty: Enum value.
    :type difficulty: str
    :param cues: Optional text.
    :type cues: str | None
    :param instructions: Optional text.
    :type instructions: str | None
    :param video_url: Optional URL.
    :type video_url: str | None
    :param is_active: Active flag.
    :type is_active: bool
    :param aliases: Optional aliases set to ensure.
    :type aliases: Iterable[str] | None
    :param tags: Optional tag names set to ensure.
    :type tags: Iterable[str] | None
    :param secondary_muscles: Optional secondary muscle set to ensure.
    :type secondary_muscles: Iterable[str] | None
    """

    name: str
    slug: str
    primary_muscle: str
    movement: str
    mechanics: str
    force: str
    unilateral: bool
    equipment: str
    grip: str | None = None
    range_of_motion: str | None = None
    difficulty: str = "BEGINNER"
    cues: str | None = None
    instructions: str | None = None
    video_url: str | None = None
    is_active: bool = True
    aliases: Iterable[str] | None = None
    tags: Iterable[str] | None = None
    secondary_muscles: Iterable[str] | None = None


@dataclass(frozen=True, slots=True)
class ExerciseGetIn:
    """
    Get by id.

    :param id: Primary key.
    :type id: int
    """

    id: int


@dataclass(frozen=True, slots=True)
class ExerciseGetBySlugIn:
    """
    Get by slug.

    :param slug: Unique slug.
    :type slug: str
    """

    slug: str


@dataclass(frozen=True, slots=True)
class ExerciseListIn:
    """
    List exercises with optional filters.

    :param pagination: Pagination input.
    :type pagination: :class:`PaginationIn`
    :param filters: Equality filters (whitelisted by repository).
    :type filters: dict[str, object] | None
    :param sort: Sort tokens (whitelisted).
    :type sort: Iterable[str] | None
    :param with_total: Compute total for pagination.
    :type with_total: bool
    """

    pagination: PaginationIn
    filters: dict[str, object] | None = None
    sort: Iterable[str] | None = None
    with_total: bool = True


@dataclass(frozen=True, slots=True)
class ExerciseUpdateScalarsIn:
    """
    Update whitelisted scalar fields for an exercise.

    :param id: Exercise PK.
    :type id: int
    :param fields: Field → value mapping (must be whitelisted by repo).
    :type fields: dict[str, object]
    """

    id: int
    fields: dict[str, object]


@dataclass(frozen=True, slots=True)
class ExerciseDeleteIn:
    """
    Delete by id (idempotent).

    :param id: Primary key.
    :type id: int
    """

    id: int


# ----------------------- Aliases / Tags / Secondary ---------------------- #


@dataclass(frozen=True, slots=True)
class AliasAddIn:
    """Add an alias."""

    exercise_id: int
    alias: str


@dataclass(frozen=True, slots=True)
class AliasRemoveIn:
    """Remove an alias."""

    exercise_id: int
    alias: str


@dataclass(frozen=True, slots=True)
class TagsSetIn:
    """Replace tag set."""

    exercise_id: int
    names: list[str]


@dataclass(frozen=True, slots=True)
class TagsAddIn:
    """Add tags without duplicates."""

    exercise_id: int
    names: list[str]


@dataclass(frozen=True, slots=True)
class TagsRemoveIn:
    """Remove specific tags or all when names=None."""

    exercise_id: int
    names: list[str] | None


@dataclass(frozen=True, slots=True)
class SecondarySetIn:
    """Replace secondary muscle set."""

    exercise_id: int
    muscles: list[str]


@dataclass(frozen=True, slots=True)
class SecondaryAddIn:
    """Add secondary muscles without duplicates."""

    exercise_id: int
    muscles: list[str]


@dataclass(frozen=True, slots=True)
class SecondaryRemoveIn:
    """Remove specific muscles or all when muscles=None."""

    exercise_id: int
    muscles: list[str] | None


@dataclass(frozen=True, slots=True)
class ListByTagIn:
    """List by tag name."""

    name: str
    sort: Iterable[str] | None = None


@dataclass(frozen=True, slots=True)
class ListBySecondaryIn:
    """List by secondary muscle."""

    muscle: str
    sort: Iterable[str] | None = None
