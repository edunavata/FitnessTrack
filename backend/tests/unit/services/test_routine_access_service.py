import pytest

from app.services._shared.errors import AuthorizationError, NotFoundError
from app.services.routines import (
    RoutineAccessService,
    SubjectRoutineActivateIn,
    SubjectRoutineListIn,
    SubjectRoutineRemoveIn,
    SubjectRoutineSaveIn,
)
from tests.factories.routine import RoutineFactory, SubjectRoutineFactory
from tests.factories.subject import SubjectFactory


@pytest.fixture()
def service() -> RoutineAccessService:
    return RoutineAccessService()


class TestRoutineAccessService:
    def test_save_public_routine(self, service, session):
        owner = SubjectFactory()
        viewer = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=True)
        session.flush()

        service.ctx.subject_id = viewer.id
        out = service.save(SubjectRoutineSaveIn(subject_id=viewer.id, routine_id=routine.id))

        assert out.subject_id == viewer.id
        assert out.routine_id == routine.id
        assert out.is_active is False

    def test_save_private_routine_forbidden_for_non_owner(self, service, session):
        owner = SubjectFactory()
        viewer = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=False)
        session.flush()

        service.ctx.subject_id = viewer.id
        with pytest.raises(AuthorizationError):
            service.save(SubjectRoutineSaveIn(subject_id=viewer.id, routine_id=routine.id))

    def test_remove_is_idempotent(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=True)
        SubjectRoutineFactory(subject=owner, routine=routine)
        session.flush()

        service.ctx.subject_id = owner.id
        first = service.remove(SubjectRoutineRemoveIn(subject_id=owner.id, routine_id=routine.id))
        second = service.remove(SubjectRoutineRemoveIn(subject_id=owner.id, routine_id=routine.id))

        assert first.removed == 1
        assert second.removed == 0

    def test_set_active_requires_visibility(self, service, session):
        owner = SubjectFactory()
        viewer = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=True)
        session.flush()

        service.ctx.subject_id = viewer.id
        service.save(SubjectRoutineSaveIn(subject_id=viewer.id, routine_id=routine.id))
        toggled = service.set_active(
            SubjectRoutineActivateIn(subject_id=viewer.id, routine_id=routine.id, is_active=True)
        )

        assert toggled.is_active is True

    def test_list_saved_returns_links(self, service, session):
        subject = SubjectFactory()
        routine_a = RoutineFactory(owner=subject, is_public=True, name="A")
        routine_b = RoutineFactory(owner=subject, is_public=True, name="B")
        SubjectRoutineFactory(subject=subject, routine=routine_a)
        SubjectRoutineFactory(subject=subject, routine=routine_b)
        session.flush()

        service.ctx.subject_id = subject.id
        out = service.list_saved(SubjectRoutineListIn(subject_id=subject.id))

        assert len(out.items) == 2
        assert {item.routine_id for item in out.items} == {routine_a.id, routine_b.id}

    def test_save_missing_routine_raises(self, service):
        subject = SubjectFactory()
        service.ctx.subject_id = subject.id
        with pytest.raises(NotFoundError):
            service.save(SubjectRoutineSaveIn(subject_id=subject.id, routine_id=9999))
