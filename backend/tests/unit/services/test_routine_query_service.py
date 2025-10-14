import pytest

from app.services._shared.dto import PaginationIn
from app.services._shared.errors import AuthorizationError, NotFoundError
from app.services.routines import (
    RoutineGetIn,
    RoutineOwnerListIn,
    RoutinePublicListIn,
    RoutineQueryService,
)
from tests.factories.routine import (
    RoutineDayExerciseFactory,
    RoutineDayFactory,
    RoutineExerciseSetFactory,
    RoutineFactory,
)
from tests.factories.subject import SubjectFactory


@pytest.fixture()
def service() -> RoutineQueryService:
    return RoutineQueryService()


class TestRoutineQueryService:
    def test_get_returns_nested_structure_for_owner(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        day = RoutineDayFactory(routine=routine, day_index=2, title="Upper Body")
        exercise = RoutineDayExerciseFactory(routine_day=day, position=3)
        RoutineExerciseSetFactory(
            routine_day_exercise=exercise,
            set_index=2,
            target_reps=12,
            target_weight_kg=42.5,
        )
        session.flush()

        service.ctx.subject_id = owner.id
        result = service.get(RoutineGetIn(routine_id=routine.id))

        assert result.id == routine.id
        assert result.owner_subject_id == owner.id
        assert [d.day_index for d in result.days] == [day.day_index]
        assert result.days[0].exercises[0].position == 3
        assert result.days[0].exercises[0].sets[0].set_index == 2
        assert result.days[0].exercises[0].sets[0].target_reps == 12

    def test_get_private_routine_requires_owner(self, service, session):
        owner = SubjectFactory()
        outsider = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        session.flush()

        service.ctx.subject_id = outsider.id
        with pytest.raises(AuthorizationError):
            service.get(RoutineGetIn(routine_id=routine.id))

    def test_get_public_allows_non_owner(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=True)
        RoutineDayFactory(routine=routine)
        session.flush()

        service.ctx.subject_id = None
        out = service.get(RoutineGetIn(routine_id=routine.id))
        assert out.id == routine.id
        assert out.is_public is True

    def test_list_by_owner_enforces_auth_and_sort(self, service, session):
        owner = SubjectFactory()
        RoutineFactory(owner=owner, name="B")
        RoutineFactory(owner=owner, name="A")
        session.flush()

        service.ctx.subject_id = owner.id
        out = service.list_by_owner(RoutineOwnerListIn(owner_subject_id=owner.id, sort=["name"]))

        assert [r.name for r in out.items] == ["A", "B"]

    def test_list_by_owner_unauthorized(self, service, session):
        owner = SubjectFactory()
        outsider = SubjectFactory()
        RoutineFactory(owner=owner)
        session.flush()

        service.ctx.subject_id = outsider.id
        with pytest.raises(AuthorizationError):
            service.list_by_owner(RoutineOwnerListIn(owner_subject_id=owner.id))

    def test_paginate_public_returns_meta(self, service, session):
        owner = SubjectFactory()
        for idx in range(3):
            RoutineFactory(owner=owner, is_public=True, name=f"Routine {idx}")
        session.flush()

        dto = RoutinePublicListIn(pagination=PaginationIn(page=1, limit=2, sort=["name"]), with_total=True)
        out = service.paginate_public(dto)

        assert out.meta.page == 1
        assert out.meta.limit == 2
        assert out.meta.total == 3
        assert out.meta.has_next is True
        assert len(out.items) == 2
        assert [r.name for r in out.items] == ["Routine 0", "Routine 1"]

    def test_get_not_found_raises(self, service):
        service.ctx.subject_id = 1
        with pytest.raises(NotFoundError):
            service.get(RoutineGetIn(routine_id=9999))
