# backend/app/repositories/exercise.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from sqlalchemy import Select, and_, delete, select
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.models.exercise import (
    Exercise,
    ExerciseAlias,
    ExerciseTag,
    Tag,
)
from app.models.exercise_secondary import ExerciseSecondaryMuscle
from app.repositories import base as base_module
from app.repositories.base import BaseRepository

apply_sorting = base_module._apply_sorting


class ExerciseRepository(BaseRepository[Exercise]):
    """
    Persistence-only repository for :class:`app.models.exercise.Exercise`.

    Focuses on safe listing, eager-loading to avoid N+1, and small domain
    helpers to maintain aliases and tags. No commits are performed here.
    """

    model = Exercise

    # ----------------------------- Sort whitelist -----------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        """
        Return safe and stable columns allowed for sorting.

        :returns: Public key → ORM attribute mapping.
        :rtype: Mapping[str, InstrumentedAttribute]
        """
        return {
            "id": self.model.id,
            "name": self.model.name,
            "slug": self.model.slug,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
            "primary_muscle": self.model.primary_muscle,
            "equipment": self.model.equipment,
            "difficulty": self.model.difficulty,
            "is_active": self.model.is_active,
        }

    # --------------------------- Filter whitelist -----------------------------
    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        """
        Restrict equality filters to a known-safe subset.

        :returns: Public key → ORM attribute mapping, or ``None`` for legacy mode.
        :rtype: Mapping[str, InstrumentedAttribute] | None
        """
        return {
            "id": self.model.id,
            "slug": self.model.slug,
            "primary_muscle": self.model.primary_muscle,
            "equipment": self.model.equipment,
            "mechanics": self.model.mechanics,
            "force": self.model.force,
            "unilateral": self.model.unilateral,
            "difficulty": self.model.difficulty,
            "is_active": self.model.is_active,
        }

    # --------------------------- Updatable whitelist --------------------------
    def _updatable_fields(self) -> set[str]:
        """
        Allow-list of safely updatable scalar fields.

        We intentionally keep ``slug`` out by default to preserve URL stability.
        Relationships (aliases/tags) are mutated via dedicated helpers.

        :returns: Set of field names.
        :rtype: set[str]
        """
        return {
            "name",
            "primary_muscle",
            "movement",
            "mechanics",
            "force",
            "unilateral",
            "equipment",
            "grip",
            "range_of_motion",
            "difficulty",
            "cues",
            "instructions",
            "video_url",
            "is_active",
        }

    # --------------------------- Default eager loading ------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        """
        Attach reasonable eager loading:

        * ``aliases`` is small (1:N, short strings) → joinedload is fine.
        * ``tags`` uses a join table → selectinload(Exercise.tags).joinedload(ExerciseTag.tag)
        * ``secondary_muscles`` can be many → selectinload (defined on model)
        """
        return stmt.options(
            selectinload(self.model.aliases),
            selectinload(self.model.tags).joinedload(ExerciseTag.tag),
            # secondary_muscles already configured with selectin
        )

    # ------------------------------- Lookups ----------------------------------
    def get_by_slug(self, slug: str) -> Exercise | None:
        """
        Fetch an exercise by its unique slug.

        :param slug: Unique slug identifier.
        :type slug: str
        :returns: The exercise or ``None``.
        :rtype: :class:`app.models.exercise.Exercise` | None
        """
        stmt = select(self.model).where(self.model.slug == slug)
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(Exercise | None, result)

    # --------------------------- Aliases maintenance --------------------------
    def add_alias(self, exercise_id: int, alias: str, *, flush: bool = True) -> ExerciseAlias:
        """
        Add a new alias to an exercise if not already present.

        :param exercise_id: Exercise PK.
        :type exercise_id: int
        :param alias: Alternative name (trimmed).
        :type alias: str
        :param flush: Whether to flush after insertion.
        :type flush: bool
        :returns: The ensured alias row.
        :rtype: :class:`app.models.exercise.ExerciseAlias`
        """
        a = alias.strip()
        if not a:
            raise ValueError("alias cannot be empty or whitespace.")

        # Check existence to avoid IntegrityError on UNIQUE(exercise_id, alias)
        stmt = select(ExerciseAlias).where(
            and_(ExerciseAlias.exercise_id == exercise_id, ExerciseAlias.alias == a)
        )
        existing_result = self.session.execute(stmt).scalars().first()
        existing = cast(ExerciseAlias | None, existing_result)
        if existing is not None:
            return existing

        row = ExerciseAlias(exercise_id=exercise_id, alias=a)
        self.session.add(row)
        if flush:
            self.flush()
        return row

    def remove_alias(self, exercise_id: int, alias: str, *, flush: bool = True) -> int:
        """
        Remove a specific alias from an exercise.

        :param exercise_id: Exercise PK.
        :type exercise_id: int
        :param alias: Alias to remove.
        :type alias: str
        :param flush: Whether to flush after deletion.
        :type flush: bool
        :returns: Number of rows removed (0 or 1).
        :rtype: int
        """
        q = (
            select(ExerciseAlias)
            .where(and_(ExerciseAlias.exercise_id == exercise_id, ExerciseAlias.alias == alias))
            .limit(1)
        )
        row = self.session.execute(q).scalars().first()
        if not row:
            return 0
        self.session.delete(row)
        if flush:
            self.flush()
        return 1

    # ------------------------------ Tags maintenance --------------------------
    def set_tags_by_names(
        self, exercise_id: int, names: list[str], *, flush: bool = True
    ) -> list[Tag]:
        """
        Replace the exercise tag set with the provided names (idempotent).

        Ensures that Tag rows exist. Adds missing links and removes extra links
        to match the provided set exactly.

        :param exercise_id: Exercise PK.
        :type exercise_id: int
        :param names: Desired tag names (case-sensitive here).
        :type names: list[str]
        :param flush: Whether to flush after changes.
        :type flush: bool
        :returns: Resulting Tag rows linked to the exercise.
        :rtype: list[:class:`app.models.exercise.Tag`]
        """
        desired = {n.strip() for n in names if n and n.strip()}
        if not desired:
            # Remove all existing
            self.remove_tags(exercise_id, None, flush=False)
            if flush:
                self.flush()
            return []

        # Load current links
        current_links = (
            self.session.execute(select(ExerciseTag).where(ExerciseTag.exercise_id == exercise_id))
            .scalars()
            .all()
        )
        current_names = {
            link.tag.name
            for link in current_links
            if link.tag is not None  # joined via eager or lazy
        }

        to_add = desired - current_names
        to_remove = current_names - desired

        # Ensure Tag rows for to_add
        tags_added: list[Tag] = []
        for name in to_add:
            tag = self._ensure_tag(name, flush=True)
            tag_id = tag.id
            if tag_id is None:
                raise RuntimeError("Ensured tag is missing a primary key after flush.")
            link = ExerciseTag(exercise_id=exercise_id, tag_id=tag_id)
            self.session.add(link)
            tags_added.append(tag)

        # Remove obsolete links
        if to_remove:
            self.remove_tags(exercise_id, list(to_remove), flush=False)

        if flush:
            self.flush()

        # Return the final set
        stmt = (
            select(Tag)
            .join(ExerciseTag, ExerciseTag.tag_id == Tag.id)
            .where(ExerciseTag.exercise_id == exercise_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def add_tags(self, exercise_id: int, names: list[str], *, flush: bool = True) -> list[Tag]:
        """
        Add (union) the given tag names to an exercise (idempotent per name).

        :returns: The full resulting tag set after additions.
        """
        cleaned = [n.strip() for n in names if n and n.strip()]
        if not cleaned:
            return self.list_tags(exercise_id)

        for name in cleaned:
            tag = self._ensure_tag(name, flush=True)
            tag_id = tag.id
            if tag_id is None:
                raise RuntimeError("Ensured tag is missing a primary key after flush.")
            # Check if link exists
            exists_stmt = select(ExerciseTag).where(
                and_(ExerciseTag.exercise_id == exercise_id, ExerciseTag.tag_id == tag_id)
            )
            if not self.session.execute(exists_stmt).scalars().first():
                self.session.add(ExerciseTag(exercise_id=exercise_id, tag_id=tag_id))

        if flush:
            self.flush()
        return self.list_tags(exercise_id)

    def remove_tags(self, exercise_id: int, names: list[str] | None, *, flush: bool = True) -> int:
        """
        Remove the specified tag names from the exercise. If ``names`` is None,
        remove **all** tags from this exercise.

        :returns: Number of removed links.
        """
        if names is None:
            # delete all links for exercise
            links = (
                self.session.execute(
                    select(ExerciseTag).where(ExerciseTag.exercise_id == exercise_id)
                )
                .scalars()
                .all()
            )
        else:
            # delete only provided
            cleaned = [n.strip() for n in names if n and n.strip()]
            if not cleaned:
                return 0
            links = (
                self.session.execute(
                    select(ExerciseTag)
                    .join(Tag, Tag.id == ExerciseTag.tag_id)
                    .where(ExerciseTag.exercise_id == exercise_id, Tag.name.in_(cleaned))
                )
                .scalars()
                .all()
            )

        count = 0
        for link in links:
            self.session.delete(link)
            count += 1
        if flush:
            self.flush()
        return count

    def list_tags(self, exercise_id: int) -> list[Tag]:
        """
        Return the current Tags linked to the given exercise.
        """
        stmt = (
            select(Tag)
            .join(ExerciseTag, ExerciseTag.tag_id == Tag.id)
            .where(ExerciseTag.exercise_id == exercise_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_tag(self, name: str, *, sort: Iterable[str] | None = None) -> list[Exercise]:
        """
        List exercises that have the provided tag name.

        :param name: Tag name.
        :type name: str
        :param sort: Public sort tokens (e.g., ``["name"]``).
        :type sort: Iterable[str] | None
        :returns: List of exercises.
        :rtype: list[:class:`app.models.exercise.Exercise`]
        """
        stmt = (
            select(self.model)
            .join(ExerciseTag, ExerciseTag.exercise_id == self.model.id)
            .join(Tag, Tag.id == ExerciseTag.tag_id)
            .where(Tag.name == name)
        )
        stmt = self._default_eagerload(stmt)

        stmt = apply_sorting(stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr())
        return list(self.session.execute(stmt).scalars().all())

    # ---------------------- Secondary muscles: helpers ----------------------
    def list_secondary_muscles(self, exercise_id: int) -> list[str]:
        """
        Return the secondary muscle names for the given exercise.
        """
        stmt = select(ExerciseSecondaryMuscle.muscle).where(
            ExerciseSecondaryMuscle.exercise_id == exercise_id
        )
        return [row[0] for row in self.session.execute(stmt).all()]

    def set_secondary_muscles(
        self, exercise_id: int, muscles: list[str], *, flush: bool = True
    ) -> list[str]:
        """
        Replace the set of secondary muscles for an exercise (idempotent).
        """
        desired = {m.strip().upper() for m in muscles if m and m.strip()}
        # load current
        current_rows = (
            self.session.execute(
                select(ExerciseSecondaryMuscle).where(
                    ExerciseSecondaryMuscle.exercise_id == exercise_id
                )
            )
            .scalars()
            .all()
        )
        current = {r.muscle for r in current_rows}

        to_add = desired - current
        to_remove = current - desired

        # add new links
        for m in to_add:
            self.session.add(ExerciseSecondaryMuscle(exercise_id=exercise_id, muscle=m))

        # remove obsolete
        if to_remove:
            self.session.execute(
                delete(ExerciseSecondaryMuscle).where(
                    and_(
                        ExerciseSecondaryMuscle.exercise_id == exercise_id,
                        ExerciseSecondaryMuscle.muscle.in_(list(to_remove)),
                    )
                )
            )

        if flush:
            self.flush()
        return sorted(desired)

    def add_secondary_muscles(
        self, exercise_id: int, muscles: list[str], *, flush: bool = True
    ) -> list[str]:
        """
        Add (union) the given secondary muscles to the exercise (idempotent).
        """
        cleaned = [m.strip().upper() for m in muscles if m and m.strip()]
        if cleaned:
            # existing set
            existing = set(self.list_secondary_muscles(exercise_id))
            for m in cleaned:
                if m not in existing:
                    self.session.add(ExerciseSecondaryMuscle(exercise_id=exercise_id, muscle=m))
            if flush:
                self.flush()
        return self.list_secondary_muscles(exercise_id)

    def remove_secondary_muscles(
        self, exercise_id: int, muscles: list[str] | None, *, flush: bool = True
    ) -> int:
        """
        Remove specific secondary muscles or all if `muscles` is None.
        :returns: number of rows removed.
        """
        if muscles is None:
            # delete all for exercise
            result = self.session.execute(
                delete(ExerciseSecondaryMuscle).where(
                    ExerciseSecondaryMuscle.exercise_id == exercise_id
                )
            )
            removed = result.rowcount or 0
        else:
            cleaned = [m.strip().upper() for m in muscles if m and m.strip()]
            if not cleaned:
                return 0
            result = self.session.execute(
                delete(ExerciseSecondaryMuscle).where(
                    and_(
                        ExerciseSecondaryMuscle.exercise_id == exercise_id,
                        ExerciseSecondaryMuscle.muscle.in_(cleaned),
                    )
                )
            )
            removed = result.rowcount or 0

        if flush:
            self.flush()
        return int(removed)

    def list_by_secondary_muscle(
        self, muscle: str, *, sort: Iterable[str] | None = None
    ) -> list[Exercise]:
        """
        List exercises that include the given secondary muscle.
        """
        m = muscle.strip().upper()
        stmt = (
            select(self.model)
            .join(
                ExerciseSecondaryMuscle,
                ExerciseSecondaryMuscle.exercise_id == self.model.id,
            )
            .where(ExerciseSecondaryMuscle.muscle == m)
        )
        stmt = self._default_eagerload(stmt)
        stmt = apply_sorting(stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr())
        return list(self.session.execute(stmt).scalars().all())

    # ------------------------------- Internals --------------------------------
    def _ensure_tag(self, name: str, *, flush: bool = True) -> Tag:
        """
        Ensure a Tag exists with the given name; create if missing.

        :param name: Tag name.
        :type name: str
        :returns: Tag row.
        :rtype: :class:`app.models.exercise.Tag`
        """
        n = name.strip()
        if not n:
            raise ValueError("tag name cannot be empty.")

        stmt = select(Tag).where(Tag.name == n)
        tag_result = self.session.execute(stmt).scalars().first()
        tag = cast(Tag | None, tag_result)
        if tag is not None:
            return tag

        tag = Tag(name=n)
        self.session.add(tag)
        if flush:
            self.flush()
        return tag
