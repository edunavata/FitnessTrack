import pytest
from sqlalchemy.orm import Session

from app.models.routine import Routine
from app.services._shared.errors import AuthorizationError, ConflictError, NotFoundError
from app.services.routines import (
    RoutineCommandService,
    RoutineCreateIn,
    RoutineDayCreateIn,
    RoutineDayExerciseAddIn,
    RoutineDeleteIn,
    RoutineSetUpsertIn,
    RoutineUpdateIn,
)
from tests.factories.exercise import ExerciseFactory
from tests.factories.routine import (
    RoutineDayExerciseFactory,
    RoutineDayFactory,
    RoutineFactory,
)
from tests.factories.subject import SubjectFactory


@pytest.fixture()
def service() -> RoutineCommandService:
    return RoutineCommandService()


class TestRoutineCommandService:
    def test_create_persists_routine(self, service, session: Session):
        owner = SubjectFactory()
        service.ctx.subject_id = owner.id

        dto = RoutineCreateIn(owner_subject_id=owner.id, name="Push", description="Upper body")
        out = service.create(dto)

        assert out.name == "Push"
        persisted = session.get(Routine, out.id)
        assert persisted is not None
        assert persisted.description == "Upper body"

    def test_create_conflict_without_idempotency(self, service, session):
        owner = SubjectFactory()
        RoutineFactory(owner=owner, name="Duplicate")
        session.flush()

        service.ctx.subject_id = owner.id
        with pytest.raises(ConflictError):
            service.create(RoutineCreateIn(owner_subject_id=owner.id, name="Duplicate"))

    def test_create_with_idempotency_returns_existing(self, service, session):
        owner = SubjectFactory()
        service.ctx.subject_id = owner.id

        dto = RoutineCreateIn(
            owner_subject_id=owner.id,
            name="Legs",
            idempotency_key="abc-123",
        )
        first = service.create(dto)
        second = service.create(dto)

        assert first.id == second.id
        assert session.query(Routine).count() == 1

    def test_update_requires_owner(self, service, session):
        owner = SubjectFactory()
        outsider = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        session.flush()

        service.ctx.subject_id = outsider.id
        with pytest.raises(AuthorizationError):
            service.update(RoutineUpdateIn(routine_id=routine.id, name="New"))

    def test_update_changes_fields(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner, description="Old", is_public=False)
        session.flush()

        service.ctx.subject_id = owner.id
        out = service.update(
            RoutineUpdateIn(routine_id=routine.id, description="Fresh", is_public=True)
        )

        assert out.description == "Fresh"
        assert out.is_public is True

    def test_delete_removes_routine(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        session.flush()

        service.ctx.subject_id = owner.id
        service.delete(RoutineDeleteIn(routine_id=routine.id))

        assert session.get(Routine, routine.id) is None

        with pytest.raises(NotFoundError):
            service.delete(RoutineDeleteIn(routine_id=routine.id))

    def test_add_day_appends_index(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        RoutineDayFactory(routine=routine, day_index=1)
        session.flush()

        service.ctx.subject_id = owner.id
        day_out = service.add_day(RoutineDayCreateIn(routine_id=routine.id, title="Day 2"))

        assert day_out.day_index == 2
        assert day_out.title == "Day 2"

    def test_add_day_exercise_assigns_position(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        day = RoutineDayFactory(routine=routine)
        exercise = ExerciseFactory()
        session.flush()

        service.ctx.subject_id = owner.id
        ex_out = service.add_day_exercise(
            RoutineDayExerciseAddIn(
                routine_day_id=day.id,
                exercise_id=exercise.id,
                notes="Warm up",
            )
        )

        assert ex_out.position == 1
        assert ex_out.notes == "Warm up"

    def test_upsert_set_inserts_and_updates(self, service, session):
        owner = SubjectFactory()
        routine = RoutineFactory(owner=owner)
        day = RoutineDayFactory(routine=routine)
        day_exercise = RoutineDayExerciseFactory(routine_day=day)
        session.flush()

        service.ctx.subject_id = owner.id
        inserted = service.upsert_set(
            RoutineSetUpsertIn(
                routine_day_exercise_id=day_exercise.id,
                set_index=1,
                target_reps=8,
            )
        )

        updated = service.upsert_set(
            RoutineSetUpsertIn(
                routine_day_exercise_id=day_exercise.id,
                set_index=1,
                target_reps=10,
                to_failure=True,
            )
        )

        assert inserted.id == updated.id
        assert updated.target_reps == 10
        assert updated.to_failure is True
