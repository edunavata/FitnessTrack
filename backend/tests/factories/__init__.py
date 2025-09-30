"""Factory Boy base classes and helpers for tests."""

from __future__ import annotations

import factory


class SQLAlchemySession:
    """Store the active SQLAlchemy session used by Factory Boy factories."""

    _session = None

    @classmethod
    def set(cls, session):
        """Register the session that factories should use for persistence."""
        cls._session = session

    @classmethod
    def get(cls):
        """Return the registered session or raise if missing."""
        if cls._session is None:
            raise RuntimeError("Factories session not set. Did you pass the 'session' fixture?")
        return cls._session


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base class ensuring factories share the pytest-managed session."""

    class Meta:
        abstract = True
        # ``sqlalchemy_session_factory`` expects a callable returning the session.
        sqlalchemy_session_factory = SQLAlchemySession.get
        sqlalchemy_session_persistence = "flush"
