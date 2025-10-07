import pytest
from app.models.user import User
from app.uow import (
    SQLAlchemyReadOnlyUnitOfWork as ROuow,
)
from app.uow import (
    SQLAlchemyUnitOfWork as RWuow,
)
from sqlalchemy import text
from tests.factories.user import UserFactory


@pytest.fixture(autouse=True)
def _skip_if_sqlite(db):
    """
    Skip tests on SQLite since database-level READ ONLY transactional flags are
    not supported there and guards would be partially ineffective.
    """
    if db.engine.url.get_backend_name() == "sqlite":
        pytest.skip("Read-only write guards not supported on SQLite")


class TestSQLAlchemyReadOnlyUnitOfWork:
    def test_blocks_orm_flush_writes(self, app, db):
        """
        Ensure that attempting to flush ORM changes inside the RO UoW raises.
        """
        with ROuow() as uow, pytest.raises(RuntimeError, match="ORM flush blocked"):
            # Add a transient object; any flush/autoflush must be blocked.
            user = UserFactory.build()  # not persisted
            uow.session.add(user)
            # Explicit flush should be intercepted by the before_flush guard.
            uow.session.flush()

    def test_blocks_core_dml(self, app, db):
        """
        Ensure that raw SQL DML/DDL is blocked inside the RO UoW.
        """
        email = UserFactory.build().email
        with ROuow() as uow, pytest.raises(RuntimeError, match="SQL statement blocked"):
            uow.session.execute(text("INSERT INTO users (email) VALUES (:email)"), {"email": email})

    def test_allows_reads(self, app, db):
        """
        Read operations should work normally within RO UoW.
        """
        # Arrange: create a persisted user using RW UoW.
        with RWuow() as uow:
            u = UserFactory.build()
            uow.session.add(u)

        # Act + Assert: can read within RO UoW.
        with ROuow() as uow:
            count = uow.session.query(User).count()
            assert count >= 1

    def test_disallows_commit(self, app, db):
        """
        RO UoW must reject commit() by design.
        """
        with ROuow() as uow, pytest.raises(RuntimeError, match="does not allow commit"):
            uow.commit()

    def test_always_rolls_back_changes(self, app, db):
        """
        Any attempted modifications must not persist after RO UoW exits.
        """
        # Arrange: create a user
        with RWuow() as uow:
            user = UserFactory.build()
            uow.session.add(user)
            uow.session.flush()
            user_id = user.id

        # Attempt to mutate inside RO scope -> should be blocked on flush
        with ROuow() as uow, pytest.raises(RuntimeError, match="ORM flush blocked"):
            u = uow.session.get(User, user_id)
            original_email = u.email
            u.email = "mutated-in-ro@example.com"
            uow.session.flush()

        # Verify persisted value remains unchanged
        with RWuow() as uow:
            persisted = uow.session.get(User, user_id)
            assert persisted.email == original_email
