# comments in English; strict reST docstrings
from __future__ import annotations

from app.models.exercise import Exercise
from app.repositories.exercise import ExerciseRepository
from app.services._shared.base import BaseService
from app.services._shared.dto import PageMeta
from app.services._shared.errors import ConflictError, NotFoundError
from app.services.exercises.dto import (
    AliasAddIn,
    AliasesOut,
    AliasRemoveIn,
    ExerciseCreateIn,
    ExerciseDeleteIn,
    ExerciseGetBySlugIn,
    ExerciseGetIn,
    ExerciseListIn,
    ExerciseListOut,
    ExerciseRowOut,
    ExerciseUpdateScalarsIn,
    ListBySecondaryIn,
    ListBySecondaryOut,
    ListByTagIn,
    ListByTagOut,
    RemoveCountOut,
    SecondaryAddIn,
    SecondaryOut,
    SecondaryRemoveIn,
    SecondarySetIn,
    TagsAddIn,
    TagsOut,
    TagsRemoveIn,
    TagsSetIn,
)
from sqlalchemy.exc import IntegrityError


class ExerciseCatalogService(BaseService):
    """
    Application service coordinating the **exercise catalog**.

    Responsibilities
    ----------------
    - Create/read/update/delete exercises (persistence-only orchestration).
    - Maintain relationships: aliases, tags and secondary muscles.
    - Provide safe pagination and whitelisted sorting/filtering.

    Notes
    -----
    - This service is framework-agnostic; no Flask/HTTP types leak here.
    - Authorization is expected at API layer (catalog is global/curated).
    - Unique constraint violations (e.g., ``slug``) are translated to
      :class:`ConflictError`.
    """

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def create(self, dto: ExerciseCreateIn) -> ExerciseRowOut:
        """
        Create an exercise and apply optional relationships atomically.

        :param dto: Creation DTO with optional aliases/tags/secondary sets.
        :type dto: :class:`ExerciseCreateIn`
        :returns: Persisted row as output projection.
        :rtype: :class:`ExerciseRowOut`
        :raises ConflictError: When slug uniqueness is violated.
        """
        try:
            with self.rw_uow() as uow:
                repo: ExerciseRepository = uow.exercises

                row = Exercise(
                    name=dto.name.strip(),
                    slug=dto.slug.strip(),
                    primary_muscle=dto.primary_muscle,
                    movement=dto.movement,
                    mechanics=dto.mechanics,
                    force=dto.force,
                    unilateral=bool(dto.unilateral),
                    equipment=dto.equipment,
                    grip=(dto.grip.strip() if dto.grip else None),
                    range_of_motion=(dto.range_of_motion.strip() if dto.range_of_motion else None),
                    difficulty=dto.difficulty,
                    cues=(dto.cues.strip() if dto.cues else None),
                    instructions=(dto.instructions.strip() if dto.instructions else None),
                    video_url=(dto.video_url.strip() if dto.video_url else None),
                    is_active=bool(dto.is_active),
                )
                repo.add(row)  # assigns PK

                # Apply relations if provided (idempotent helpers in repo)
                if dto.aliases:
                    for a in dto.aliases:
                        repo.add_alias(row.id, a, flush=False)
                if dto.tags is not None:
                    repo.set_tags_by_names(row.id, list(dto.tags), flush=False)
                if dto.secondary_muscles is not None:
                    repo.set_secondary_muscles(row.id, list(dto.secondary_muscles), flush=False)

                # Commit on context exit
                return self._to_row_out(row)
        except IntegrityError as ie:
            # UQ slug (name uq_exercises_slug)
            if "uq_exercises_slug" in str(ie.orig).lower():
                raise ConflictError("Exercise", "slug already exists") from ie
            raise ConflictError("Exercise", "conflict") from ie

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get(self, dto: ExerciseGetIn) -> ExerciseRowOut:
        """
        Retrieve a single exercise by id.

        :param dto: Get DTO.
        :type dto: :class:`ExerciseGetIn`
        :returns: Exercise projection.
        :rtype: :class:`ExerciseRowOut`
        :raises NotFoundError: When id does not exist.
        """
        with self.ro_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            row = repo.get(dto.id)
            if row is None:
                raise NotFoundError("Exercise", dto.id)
            return self._to_row_out(row)

    def get_by_slug(self, dto: ExerciseGetBySlugIn) -> ExerciseRowOut:
        """
        Retrieve a single exercise by slug.

        :param dto: Get by slug DTO.
        :type dto: :class:`ExerciseGetBySlugIn`
        :returns: Exercise projection.
        :rtype: :class:`ExerciseRowOut`
        :raises NotFoundError: When slug does not exist.
        """
        with self.ro_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            row = repo.get_by_slug(dto.slug)
            if row is None:
                raise NotFoundError("Exercise", dto.slug)
            return self._to_row_out(row)

    def list(self, dto: ExerciseListIn) -> ExerciseListOut:
        """
        List/paginate exercises with optional filters and sorting.

        :param dto: Listing DTO.
        :type dto: :class:`ExerciseListIn`
        :returns: Paginated list.
        :rtype: :class:`ExerciseListOut`
        """
        with self.ro_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            pagination = self.ensure_pagination(
                page=dto.pagination.page, limit=dto.pagination.limit, sort=dto.sort
            )
            page = repo.paginate(
                pagination=pagination,
                filters=dto.filters or {},
                with_total=dto.with_total,
            )
            items = [self._to_row_out(r) for r in page.items]
            meta = PageMeta(
                page=page.page,
                limit=page.limit,
                total=page.total,
                has_prev=page.page > 1,
                has_next=(page.page * page.limit) < page.total if dto.with_total else False,
            )
            return ExerciseListOut(items=items, meta=meta)

    def list_by_tag(self, dto: ListByTagIn) -> ListByTagOut:
        """
        List exercises associated with a given tag.

        :param dto: List-by-tag DTO.
        :type dto: :class:`ListByTagIn`
        :returns: Matching exercises.
        :rtype: :class:`ListByTagOut`
        """
        with self.ro_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            items = repo.list_by_tag(dto.name, sort=dto.sort)
            return ListByTagOut(items=[self._to_row_out(r) for r in items])

    def list_by_secondary(self, dto: ListBySecondaryIn) -> ListBySecondaryOut:
        """
        List exercises by a secondary muscle.

        :param dto: List-by-secondary DTO.
        :type dto: :class:`ListBySecondaryIn`
        :returns: Matching exercises.
        :rtype: :class:`ListBySecondaryOut`
        """
        with self.ro_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            items = repo.list_by_secondary_muscle(dto.muscle, sort=dto.sort)
            return ListBySecondaryOut(items=[self._to_row_out(r) for r in items])

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    def update_scalars(self, dto: ExerciseUpdateScalarsIn) -> ExerciseRowOut:
        """
        Update whitelisted scalar fields.

        :param dto: Update DTO.
        :type dto: :class:`ExerciseUpdateScalarsIn`
        :returns: Updated projection.
        :rtype: :class:`ExerciseRowOut`
        :raises NotFoundError: If the exercise does not exist.
        :raises ConflictError: On unique constraint conflicts (e.g., slug if allowed).
        """
        try:
            with self.rw_uow() as uow:
                repo: ExerciseRepository = uow.exercises
                row = repo.get(dto.id)
                if row is None:
                    raise NotFoundError("Exercise", dto.id)
                repo.assign_updates(row, dto.fields, flush=True)
                return self._to_row_out(row)
        except IntegrityError as ie:
            if "uq_exercises_slug" in str(ie.orig).lower():
                # Translate to domain-level conflict without leaking driver details
                raise ConflictError("Exercise", "slug already exists") from ie
            raise

    # ---------------------------- Aliases -------------------------------- #

    def add_alias(self, dto: AliasAddIn) -> AliasesOut:
        """
        Add a new alias; idempotent if already exists.

        :param dto: Add-alias DTO.
        :type dto: :class:`AliasAddIn`
        :returns: Current alias list (sorted).
        :rtype: :class:`AliasesOut`
        :raises NotFoundError: If exercise does not exist.
        """
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            row = repo.get(dto.exercise_id)
            if row is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            repo.add_alias(dto.exercise_id, dto.alias, flush=True)
            return AliasesOut(aliases=sorted([a.alias for a in row.aliases]))

    def remove_alias(self, dto: AliasRemoveIn) -> RemoveCountOut:
        """
        Remove an alias; returns removed count (0/1).

        :param dto: Remove-alias DTO.
        :type dto: :class:`AliasRemoveIn`
        :returns: Removal result with count.
        :rtype: :class:`RemoveCountOut`
        :raises NotFoundError: If exercise does not exist.
        """
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            removed = repo.remove_alias(dto.exercise_id, dto.alias, flush=True)
            return RemoveCountOut(removed=removed)

    # ----------------------------- Tags ---------------------------------- #

    def set_tags(self, dto: TagsSetIn) -> TagsOut:
        """Replace tag set and return final sorted names."""
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            tags = repo.set_tags_by_names(dto.exercise_id, dto.names, flush=True)
            return TagsOut(tags=sorted([t.name for t in tags]))

    def add_tags(self, dto: TagsAddIn) -> TagsOut:
        """Union tags and return final sorted names."""
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            tags = repo.add_tags(dto.exercise_id, dto.names, flush=True)
            return TagsOut(tags=sorted([t.name for t in tags]))

    def remove_tags(self, dto: TagsRemoveIn) -> RemoveCountOut:
        """Remove specific tags (or all when names=None). Return count removed."""
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            removed = repo.remove_tags(dto.exercise_id, dto.names, flush=True)
            return RemoveCountOut(removed=removed)

    # ----------------------- Secondary muscles --------------------------- #

    def set_secondary(self, dto: SecondarySetIn) -> SecondaryOut:
        """Replace secondary muscles with the provided set (sorted)."""
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            muscles = repo.set_secondary_muscles(dto.exercise_id, dto.muscles, flush=True)
            return SecondaryOut(secondary_muscles=sorted(muscles))

    def add_secondary(self, dto: SecondaryAddIn) -> SecondaryOut:
        """Add secondary muscles without duplicates (sorted)."""
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            muscles = repo.add_secondary_muscles(dto.exercise_id, dto.muscles, flush=True)
            return SecondaryOut(secondary_muscles=sorted(muscles))

    def remove_secondary(self, dto: SecondaryRemoveIn) -> RemoveCountOut:
        """Remove specific secondary muscles (or all when None). Return count removed."""
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            if repo.get(dto.exercise_id) is None:
                raise NotFoundError("Exercise", dto.exercise_id)
            removed = repo.remove_secondary_muscles(dto.exercise_id, dto.muscles, flush=True)
            return RemoveCountOut(removed=removed)

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete(self, dto: ExerciseDeleteIn) -> None:
        """
        Delete an exercise by idempotent semantics.

        :param dto: Delete DTO.
        :type dto: :class:`ExerciseDeleteIn`
        :returns: ``None``.
        :rtype: None
        """
        with self.rw_uow() as uow:
            repo: ExerciseRepository = uow.exercises
            row = repo.get(dto.id)
            if row is None:
                return
            repo.delete(row)
            # commit on exit

    # ------------------------------------------------------------------ #
    # Mapping
    # ------------------------------------------------------------------ #

    def _to_row_out(self, row: Exercise) -> ExerciseRowOut:
        """
        Map ORM Exercise to :class:`ExerciseRowOut`.

        :param row: ORM instance.
        :type row: :class:`app.models.exercise.Exercise`
        :returns: Output projection.
        :rtype: :class:`ExerciseRowOut`
        """
        aliases = sorted([a.alias for a in (row.aliases or [])])
        tags = sorted([t.tag.name for t in (row.tags or []) if t.tag is not None])
        # Use repo helper for secondary muscles to avoid lazy pitfalls when needed
        secondaries = sorted([sm.muscle for sm in (row.secondary_muscles or [])])

        return ExerciseRowOut(
            id=row.id,
            name=row.name,
            slug=row.slug,
            primary_muscle=row.primary_muscle,
            movement=row.movement,
            mechanics=row.mechanics,
            force=row.force,
            unilateral=row.unilateral,
            equipment=row.equipment,
            grip=row.grip,
            range_of_motion=row.range_of_motion,
            difficulty=row.difficulty,
            cues=row.cues,
            instructions=row.instructions,
            video_url=row.video_url,
            is_active=row.is_active,
            aliases=aliases,
            tags=tags,
            secondary_muscles=secondaries,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
