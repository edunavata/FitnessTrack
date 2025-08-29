"""Global pytest fixtures for the FitnessTrack API."""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any, Callable

import pytest
from flask import Flask
from sqlalchemy import event

# Ensure the ``backend`` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import create_app  # noqa: E402
from app.core.database import db  # noqa: E402
from app.models.user import User  # noqa: E402

from tests.factories.user import UserFactory  # noqa: E402
from tests.helpers.auth import expired_token, issue_token  # noqa: E402


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create and configure a Flask application for tests.

    Returns
    -------
    Generator[Flask, None, None]
        Configured Flask application instance.
    """

    os.environ.setdefault("APP_ENV", "testing")
    application = create_app()
    with application.app_context():
        yield application


@pytest.fixture(scope="session")
def _db(app: Flask) -> Generator[Any, None, None]:
    """Initialize the database schema for the test session."""

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def session(_db: Any) -> Generator[Any, None, None]:
    """Provide a transactional database session for a test case."""

    connection = _db.engine.connect()
    transaction = connection.begin()
    sess = _db.create_scoped_session({"bind": connection, "binds": {}})
    _db.session = sess

    nested = connection.begin_nested()

    @event.listens_for(sess(), "after_transaction_end")
    def restart_savepoint(_: Any, trans: Any) -> None:  # pragma: no cover - event hook
        if trans.nested and not trans._parent.nested:
            nonlocal nested
            nested = connection.begin_nested()

    try:
        yield sess
    finally:
        sess.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(app: Flask) -> Generator[Any, None, None]:
    """Return a Flask test client."""

    return app.test_client()


@pytest.fixture()
def user(session: Any) -> User:
    """Persist and return a user instance."""

    return UserFactory()


@pytest.fixture()
def auth_token(app: Flask, user: User) -> str:
    """Generate a valid JWT for ``user``."""

    with app.app_context():
        return issue_token(user.id)


@pytest.fixture()
def auth_header(auth_token: str) -> dict[str, str]:
    """Authorization header for authenticated requests."""

    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def expired_auth_token(app: Flask, user: User) -> str:
    """Return an already expired JWT for ``user``."""

    with app.app_context():
        return expired_token(user.id)


@pytest.fixture()
def freeze_time() -> Callable[[str | None], Any]:
    """Factory returning :func:`freezegun.freeze_time`.

    Examples
    --------
    >>> def test_with_frozen_time(freeze_time):
    ...     with freeze_time("2024-01-01"):
    ...         ...
    """

    from freezegun import freeze_time as _freeze_time

    def _factory(target: str | None = None) -> Any:
        return _freeze_time(target or "2024-01-01")

    return _factory

