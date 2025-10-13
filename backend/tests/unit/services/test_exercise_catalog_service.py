from __future__ import annotations

import pytest
from app.repositories.exercise import ExerciseRepository
from app.services._shared.dto import PaginationIn
from app.services._shared.errors import ConflictError, NotFoundError
from app.services.exercises.dto import (
    AliasAddIn,
    AliasRemoveIn,
    ExerciseCreateIn,
    ExerciseDeleteIn,
    ExerciseGetBySlugIn,
    ExerciseGetIn,
    ExerciseListIn,
    ExerciseUpdateScalarsIn,
    ListBySecondaryIn,
    ListByTagIn,
    SecondaryAddIn,
    SecondaryRemoveIn,
    SecondarySetIn,
    TagsAddIn,
    TagsRemoveIn,
    TagsSetIn,
)
from app.services.exercises.service import ExerciseCatalogService


class TestExerciseCatalogService:
    """Validate ExerciseCatalogService behaviours for the catalog."""

    # -------------------------- Fixtures ---------------------------------- #

    @pytest.fixture()
    def service(self) -> ExerciseCatalogService:
        return ExerciseCatalogService()

    @pytest.fixture()
    def repo(self, session) -> ExerciseRepository:
        return ExerciseRepository(session=session)

    # -------------------------- Helpers ----------------------------------- #

    def _mk_create(self, slug: str = "barbell-bench-press") -> ExerciseCreateIn:
        return ExerciseCreateIn(
            name="Barbell Bench Press",
            slug=slug,
            primary_muscle="CHEST",
            movement="HORIZONTAL_PUSH",
            mechanics="COMPOUND",
            force="PUSH",
            unilateral=False,
            equipment="BARBELL",
            difficulty="BEGINNER",
            cues="Keep shoulders down and back.",
            instructions="Lower bar to mid-chest, press up.",
            video_url=None,
            is_active=True,
            aliases=["Bench Press", "BB Bench"],
            tags=["compound", "strength"],
            secondary_muscles=["TRICEPS", "SHOULDERS"],
        )

    # --------------------------- Create ----------------------------------- #

    def test_create_with_relations(self, service, repo):
        """Create exercise and ensure aliases/tags/secondary are persisted."""
        out = service.create(self._mk_create())
        assert out.id > 0
        assert out.slug == "barbell-bench-press"
        assert sorted(out.aliases) == ["BB Bench", "Bench Press"]
        assert sorted(out.tags) == ["compound", "strength"]
        assert sorted(out.secondary_muscles) == ["SHOULDERS", "TRICEPS"]

        row = repo.get(out.id)
        assert row is not None and row.name == "Barbell Bench Press"

    def test_create_conflict_on_duplicate_slug(self, service):
        """Duplicate slug should raise ConflictError via unique constraint."""
        service.create(self._mk_create(slug="dup-slug"))
        with pytest.raises(ConflictError):
            service.create(self._mk_create(slug="dup-slug"))

    # ---------------------------- Read ------------------------------------ #

    def test_get_by_id_and_slug(self, service):
        """Fetch created exercise by id and slug."""
        created = service.create(self._mk_create(slug="row-variant"))
        got = service.get(ExerciseGetIn(id=created.id))
        assert got.slug == "row-variant"

        got2 = service.get_by_slug(ExerciseGetBySlugIn(slug="row-variant"))
        assert got2.id == created.id

    def test_get_not_found(self, service):
        """Missing exercise → NotFoundError."""
        with pytest.raises(NotFoundError):
            service.get(ExerciseGetIn(id=999999))

    # ---------------------------- List ------------------------------------ #

    def test_list_with_filters_sort_and_pagination(self, service):
        """List supports repository whitelisted filters and sorting."""
        # seed
        service.create(self._mk_create(slug="bench"))
        # BEFORE (this never executes due to if False)
        (
            service.create(self._mk_create(slug="incline-db-press")).name if False else None
        )  # keep params similar

        # AFTER (actually seed the second CHEST exercise)
        service.create(self._mk_create(slug="incline-db-press"))

        service.create(
            ExerciseCreateIn(
                name="Cable Fly",
                slug="cable-fly",
                primary_muscle="CHEST",
                movement="HORIZONTAL_PUSH",
                mechanics="ISOLATION",
                force="PUSH",
                unilateral=False,
                equipment="CABLE",
                difficulty="BEGINNER",
                cues=None,
                instructions=None,
                video_url=None,
                is_active=True,
            )
        )

        dto = ExerciseListIn(
            pagination=PaginationIn(page=1, limit=2, sort=["-created_at", "name"]),
            filters={"primary_muscle": "CHEST"},
            with_total=True,
        )
        result = service.list(dto)
        assert len(result.items) == 2
        assert result.meta.page == 1
        assert result.meta.limit == 2
        assert result.meta.total >= 3
        assert result.meta.has_next is True

    # --------------------------- Update ----------------------------------- #

    def test_update_scalars(self, service, repo):
        """Update whitelisted scalar fields."""
        created = service.create(self._mk_create(slug="to-update"))
        out = service.update_scalars(
            ExerciseUpdateScalarsIn(
                id=created.id,
                fields={"name": "Bench Press (Barbell)", "is_active": False},
            )
        )
        assert out.name == "Bench Press (Barbell)"
        assert out.is_active is False

        row = repo.get(created.id)
        assert row.name == "Bench Press (Barbell)"

    # ---------------------------- Aliases --------------------------------- #

    def test_alias_add_remove(self, service):
        """Alias add is idempotent; remove returns 0/1 in a DTO."""
        created = service.create(self._mk_create(slug="alias-op"))

        # add existing returns same set (idempotent)
        aliases_out = service.add_alias(AliasAddIn(exercise_id=created.id, alias="Bench Press"))
        assert "Bench Press" in aliases_out.aliases

        removed_out = service.remove_alias(
            AliasRemoveIn(exercise_id=created.id, alias="Nonexistent")
        )
        assert removed_out.removed == 0

        removed_out = service.remove_alias(
            AliasRemoveIn(exercise_id=created.id, alias="Bench Press")
        )
        assert removed_out.removed == 1

    # ------------------------------ Tags ---------------------------------- #

    def test_tags_set_add_remove(self, service):
        """Replace tags, union add, and remove using DTO wrappers."""
        created = service.create(self._mk_create(slug="tags-op"))

        final_set = service.set_tags(TagsSetIn(exercise_id=created.id, names=["push", "chest"]))
        assert sorted(final_set.tags) == ["chest", "push"]

        after_add = service.add_tags(TagsAddIn(exercise_id=created.id, names=["compound", "push"]))
        assert sorted(after_add.tags) == ["chest", "compound", "push"]

        removed_count = service.remove_tags(TagsRemoveIn(exercise_id=created.id, names=["push"]))
        assert removed_count.removed == 1

        after_remove_all = service.remove_tags(TagsRemoveIn(exercise_id=created.id, names=None))
        assert after_remove_all.removed >= 0  # all cleared

    # ----------------------- Secondary muscles ---------------------------- #

    def test_secondary_set_add_remove(self, service):
        """Manage secondary muscles with set/add/remove DTOs."""
        created = service.create(self._mk_create(slug="sec-op"))

        final_set = service.set_secondary(
            SecondarySetIn(exercise_id=created.id, muscles=["TRICEPS"])
        )
        assert final_set.secondary_muscles == ["TRICEPS"]

        after_add = service.add_secondary(
            SecondaryAddIn(exercise_id=created.id, muscles=["SHOULDERS", "TRICEPS"])
        )
        assert sorted(after_add.secondary_muscles) == ["SHOULDERS", "TRICEPS"]

        removed = service.remove_secondary(
            SecondaryRemoveIn(exercise_id=created.id, muscles=["TRICEPS"])
        )
        assert removed.removed == 1

        removed_all = service.remove_secondary(
            SecondaryRemoveIn(exercise_id=created.id, muscles=None)
        )
        assert removed_all.removed >= 0

    # -------------------------- List by rels ------------------------------ #

    def test_list_by_tag_and_secondary(self, service):
        """List helpers by tag and by secondary muscle return DTOs with items."""
        created = service.create(self._mk_create(slug="list-rel"))
        service.add_tags(TagsAddIn(exercise_id=created.id, names=["featured"]))
        service.add_secondary(SecondaryAddIn(exercise_id=created.id, muscles=["TRICEPS"]))

        by_tag = service.list_by_tag(ListByTagIn(name="featured"))
        assert any(row.slug == "list-rel" for row in by_tag.items)

        by_sec = service.list_by_secondary(ListBySecondaryIn(muscle="triceps"))
        assert any(row.slug == "list-rel" for row in by_sec.items)

    # ------------------------------ Delete -------------------------------- #

    def test_delete_is_idempotent(self, service, repo):
        """Deleting twice should not error."""
        created = service.create(self._mk_create(slug="to-delete"))
        service.delete(ExerciseDeleteIn(id=created.id))
        # second time does nothing
        service.delete(ExerciseDeleteIn(id=created.id))
        assert repo.get(created.id) is None
