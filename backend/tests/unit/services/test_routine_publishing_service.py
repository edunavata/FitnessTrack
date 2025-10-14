import pytest

from app.services._shared.errors import AuthorizationError, NotFoundError, PreconditionFailedError
from app.services.routines import RoutinePublishIn, RoutinePublishingService
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import RoutineDayExerciseFactory, RoutineDayFactory, RoutineFactory
from tests.factories.subject import SubjectFactory


@pytest.fixture()
def service() -> RoutinePublishingService:
    return RoutinePublishingService()


class TestRoutinePublishingService:
    def test_publish_requires_structure(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=False)
        day = RoutineDayFactory(routine=routine)
        RoutineDayExerciseFactory(routine_day=day, exercise=ExerciseFactory())
        session.flush()

        service.ctx.subject_id = owner.id
        out = service.set_public(RoutinePublishIn(routine_id=routine.id, make_public=True))

        assert out.is_public is True

    def test_publish_without_exercises_raises_precondition(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=False)
        RoutineDayFactory(routine=routine)
        session.flush()

        service.ctx.subject_id = owner.id
        with pytest.raises(PreconditionFailedError):
            service.set_public(RoutinePublishIn(routine_id=routine.id, make_public=True))

    def test_unpublish_is_idempotent(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner, is_public=True)
        session.flush()

        service.ctx.subject_id = owner.id
        out = service.set_public(RoutinePublishIn(routine_id=routine.id, make_public=False))
        assert out.is_public is False

        # repeat without error
        out2 = service.set_public(RoutinePublishIn(routine_id=routine.id, make_public=False))
        assert out2.is_public is False

    def test_publish_requires_owner(self, service, session):
        owner = SubjectFactory()
        outsider = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        session.flush()

        service.ctx.subject_id = outsider.id
        with pytest.raises(AuthorizationError):
            service.set_public(RoutinePublishIn(routine_id=routine.id, make_public=True))

    def test_publish_not_found(self, service):
        service.ctx.subject_id = 1
        with pytest.raises(NotFoundError):
            service.set_public(RoutinePublishIn(routine_id=9999, make_public=True))
