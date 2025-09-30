"""Pytest fixtures configuring isolated SQLAlchemy sessions for tests.

Tables are created once per session against an in-memory SQLite database and
each test is wrapped in a SAVEPOINT-based transaction that is rolled back.
"""

from __future__ import annotations

import os

import pytest
from app.core.database import db as _db  # Flask-SQLAlchemy database instance
from app.factory import create_app  # Application factory under test
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker


class TestConfig:
    """Testing configuration applied to the Flask application factory.

    Notes
    -----
    - Uses an in-memory SQLite database for speed.
    - Disables CSRF and debugging noise.
    - Avoids hitting external services.
    """

    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture(scope="session")
def app():
    """Provide a Flask application configured for testing.

    Returns
    -------
    flask.Flask
        Application instance with :class:`TestConfig` applied.
    """
    # Ensure env-based config does not leak into tests
    os.environ.pop("DATABASE_URL", None)
    app = create_app(TestConfig)
    app.logger.setLevel("WARNING")
    return app


@pytest.fixture(scope="session")
def db(app):
    """Provide the SQLAlchemy database bound to the testing app.

    Yields
    ------
    flask_sqlalchemy.SQLAlchemy
        Database object with tables created for the session.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="session")
def connection(db):
    """Keep a single DBAPI connection open for the whole session.

    Notes
    -----
    The shared connection allows nested transactions so each test runs inside
    its own SAVEPOINT.
    """
    conn = db.engine.connect()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="function")
def session(db, connection):
    """Provide a SQLAlchemy session with a nested transaction per test.

    Notes
    -----
    Pattern (SQLAlchemy 2.0):

    - Begin a top-level transaction on the shared connection.
    - Create a ``scoped_session`` bound to that connection.
    - Start a nested transaction (SAVEPOINT) for the test.
    - Re-open the SAVEPOINT automatically when it ends.
    - Roll back everything after the test and restore ``db.session``.

    Yields
    ------
    sqlalchemy.orm.scoping.scoped_session
        Session usable in tests; rolled back after each test.
    """
    # 1) Top-level transaction
    top_trans = connection.begin()

    # 2) Scoped session bound to the connection
    SessionFactory = sessionmaker(bind=connection, future=True)
    scoped = scoped_session(SessionFactory)

    # 3) SAVEPOINT per test
    nested = connection.begin_nested()

    # 4) Re-create SAVEPOINT when the previous nested transaction ends
    @event.listens_for(scoped(), "after_transaction_end")
    def _restart_savepoint(sess, trans):  # pragma: no cover
        if trans.nested and not trans._parent.nested:
            nonlocal nested
            nested = connection.begin_nested()

    # 5) Monkey-patch db.session so app code uses this scoped session
    original_session = db.session
    db.session.remove()
    db.session = scoped

    try:
        yield scoped
    finally:
        scoped.remove()
        db.session = original_session
        top_trans.rollback()


@pytest.fixture(scope="session")
def faker():
    """Provide a ``Faker`` instance seeded for deterministic tests.

    Returns
    -------
    faker.Faker
        Faker generator seeded with a stable value.
    """
    from faker import Faker

    fk = Faker()
    Faker.seed(1337)
    return fk


# -- Hook up Factory Boy to pytest SQLAlchemy session --------------------------
@pytest.fixture(autouse=True)
def _factories_session(session):
    """Ensure Factory Boy uses the transactional SQLAlchemy session.

    Parameters
    ----------
    session: scoped_session
        Session fixture injected automatically to wire Factory Boy.
    """

    from tests.factories import SQLAlchemySession

    SQLAlchemySession.set(session)
    yield
