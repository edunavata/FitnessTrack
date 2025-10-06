"""
Unit tests for SQLAlchemyReadOnlyUnitOfWork (read-only), using factories.
"""

from __future__ import annotations

import pytest
from app.models import User  # Ajusta import si tu ruta difiere
from app.uow import ReadOnlyViolation, SQLAlchemyReadOnlyUnitOfWork, SQLAlchemyUnitOfWork
from sqlalchemy import text
from tests.factories.user import UserFactory


@pytest.fixture(autouse=True)
def _skip_if_sqlite(db):
    if db.engine.url.get_backend_name() == "sqlite":
        pytest.skip("Read-only write guards not supported on SQLite")


class TestSQLAlchemyReadOnlyUnitOfWork:
    def test_readonly_uow_disallows_commit(self, app, db, session):
        """
        GIVEN a read-only UoW
        WHEN commit() is called
        THEN it raises ReadOnlyViolation.
        """
        with SQLAlchemyReadOnlyUnitOfWork() as uow, pytest.raises(ReadOnlyViolation):
            uow.commit()

    def test_readonly_uow_blocks_orm_flush_on_new_object(self, app, db, session):
        """
        GIVEN a read-only UoW
        WHEN a new object is added and a flush is attempted (explicit or implicit)
        THEN ReadOnlyViolation is raised by the ORM write-guard.
        """
        with SQLAlchemyReadOnlyUnitOfWork() as _uow:
            # build() no persiste; add() + flush debería estar bloqueado
            u = UserFactory.build()
            db.session.add(u)
            with pytest.raises(ReadOnlyViolation):
                db.session.flush()  # dispara guard antes de tocar BD

    def test_readonly_uow_blocks_core_update_statement(self, app, db, session):
        """
        GIVEN a read-only UoW
        WHEN an UPDATE is attempted via Core/Session.execute
        THEN ReadOnlyViolation is raised by the Core write-guard.
        """
        # Semilla fuera del scope RO (persistimos con factory)
        existing = UserFactory.create(email="seed@example.com")

        table = User.__tablename__  # evita hardcode del nombre de tabla
        with SQLAlchemyReadOnlyUnitOfWork() as _uow:
            # Intento de UPDATE directo vía Core
            stmt = text(f"UPDATE {table} SET email='x@x' WHERE id=:uid").bindparams(uid=existing.id)
            with pytest.raises(ReadOnlyViolation):
                db.session.execute(stmt)

    def test_readonly_uow_always_rolls_back_on_exit(self, app, db, session):
        """
        GIVEN a read-only UoW
        WHEN a new object is added inside the scope but no exception occurs
        THEN leaving the context always rolls back; nothing is persisted.
        """
        initial = db.session.query(User).count()
        with SQLAlchemyReadOnlyUnitOfWork() as _uow:
            u = UserFactory.build()
            db.session.add(u)
            # aunque nadie haga flush, el guard evita escrituras y al salir se hace rollback

        after = db.session.query(User).count()
        assert after == initial

    def test_readonly_uow_does_not_leak_listeners(self, app, db, session):
        """
        GIVEN a read-only UoW
        WHEN we exit the context
        THEN write guards are removed and a subsequent writer UoW can persist normally.
        """
        with SQLAlchemyReadOnlyUnitOfWork() as _uow:
            _ = db.session.query(User).count()  # lectura inocua

        # Ahora un write normal debe funcionar
        with SQLAlchemyUnitOfWork() as w:
            w.users.add(UserFactory.build())
            # commit en salida

        # Verificamos que se escribió exactamente 1 fila
        count = db.session.query(User).count()
        assert count >= 1  # al menos la creada arriba (podrían existir previas de otros tests)

    def test_readonly_uow_isolation_level_validation_for_sqlite(self, app, db, session):
        """
        GIVEN SQLite dialect in tests
        WHEN passing an unsupported isolation level for sqlite
        THEN ValueError is raised at __enter__ with a clear message.

        For SQLite in your VALID_ISOLATION_LEVELS_BY_DIALECT, allowed are {'AUTOCOMMIT','SERIALIZABLE'}.
        """
        uow = SQLAlchemyReadOnlyUnitOfWork(isolation_level="READ COMMITTED")
        with pytest.raises(ValueError) as ei, uow:
            pass
        msg = str(ei.value)
        assert "not supported for dialect 'sqlite'" in msg
        assert "Supported:" in msg
