"""
Unit tests for SQLAlchemyUnitOfWork (writer), using factories.
"""

from __future__ import annotations

import pytest
from app.models import User  # Ajusta import si tu ruta difiere
from app.uow import SQLAlchemyUnitOfWork
from tests.factories.user import UserFactory


class TestSQLAlchemyUnitOfWorkWriter:
    def test_writer_uow_commits_on_success(self, app, db, session):
        """
        GIVEN a writer UoW
        WHEN we create a user via repo inside the context and leave without exception
        THEN the transaction is committed and the row is visible afterwards.
        """
        initial = db.session.query(User).count()

        with SQLAlchemyUnitOfWork() as uow:
            # Usamos la factory para construir la entidad
            u = UserFactory.build()  # build = no persist
            uow.users.add(u)
            # exit sin excepción -> commit()

        after = db.session.query(User).count()
        assert after == initial + 1

    def test_writer_uow_rolls_back_on_exception(self, app, db, session):
        """
        GIVEN a writer UoW
        WHEN an exception is raised inside the context
        THEN the transaction is rolled back and no rows are persisted.
        """
        initial = db.session.query(User).count()

        with pytest.raises(RuntimeError), SQLAlchemyUnitOfWork() as uow:
            u = UserFactory.build()
            uow.users.add(u)
            raise RuntimeError("boom")  # fuerza rollback

        after = db.session.query(User).count()
        assert after == initial
