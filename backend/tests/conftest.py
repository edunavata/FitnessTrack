"""Pytest fixtures configuring an isolated transactional database layer.

Each test runs inside a SAVEPOINT-backed transaction against an in-memory
SQLite database so data changes never leak between cases.
"""

from __future__ import annotations

import os

import pytest
from app.core.extensions import db as _db  # Flask-SQLAlchemy instance
from app.factory import create_app  # application factory under test
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker


class TestConfig:
    """Testing configuration for creating the Flask app.

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
    """Create a Flask application configured for testing.

    Returns
    -------
    flask.Flask
        Application instance with :class:`TestConfig` applied and logging
        noise reduced.
    """
    # Ensure env-based config does not leak into tests
    os.environ.pop("DATABASE_URL", None)
    app = create_app(TestConfig)
    app.logger.setLevel("WARNING")
    return app


@pytest.fixture(scope="session")
def db(app):
    """Create database tables once per test session.

    Parameters
    ----------
    app: flask.Flask
        Application fixture ensuring the Flask context is available.

    Yields
    ------
    flask_sqlalchemy.SQLAlchemy
        Database extension bound to the testing application.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="session")
def connection(db):
    """Keep a dedicated DBAPI connection open for the whole session.

    Parameters
    ----------
    db: flask_sqlalchemy.SQLAlchemy
        Database extension used to retrieve the engine.

    Yields
    ------
    sqlalchemy.engine.Connection
        Connection reused by nested transactions in each test.
    """
    conn = db.engine.connect()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="function")
def session(db, connection):
    """Provide a SQLAlchemy session wrapped in a nested transaction.

    Parameters
    ----------
    db: flask_sqlalchemy.SQLAlchemy
        Database extension whose ``session`` attribute is temporarily
        reassigned.
    connection: sqlalchemy.engine.Connection
        Shared connection maintaining the outer transaction.

    Yields
    ------
    sqlalchemy.orm.scoping.scoped_session
        Scoped session bound to the shared connection; automatically rolled
        back after each test.

    Notes
    -----
    The fixture mirrors the SQLAlchemy 2.0 pattern for transactional tests: it
    begins a top-level transaction, starts a SAVEPOINT per test, and reinstalls
    the SAVEPOINT whenever SQLAlchemy ends one.
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
    """Provide a :class:`faker.Faker` instance seeded for deterministic tests."""
    from faker import Faker

    fk = Faker()
    Faker.seed(1337)
    return fk


# -- Hook up Factory Boy to pytest SQLAlchemy session --------------------------
@pytest.fixture(autouse=True)
def _factories_session(session):
    """Wire Factory Boy's session helper to the transactional session fixture."""
    from tests.factories import SQLAlchemySession

    SQLAlchemySession.set(session)
    yield
