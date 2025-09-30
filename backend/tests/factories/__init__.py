"""Factory Boy helpers wired to the project's SQLAlchemy session."""

from __future__ import annotations

import factory


class SQLAlchemySession:
    """Store the session provided by the pytest fixture layer."""

    _session = None

    @classmethod
    def set(cls, session):
        """Register the SQLAlchemy session used to persist factory objects."""
        cls._session = session

    @classmethod
    def get(cls):
        """Return the registered SQLAlchemy session.

        Returns
        -------
        sqlalchemy.orm.scoping.scoped_session
            Session configured for nested transactions in tests.

        Raises
        ------
        RuntimeError
            If factories are used without the ``session`` fixture wiring.
        """
        if cls._session is None:
            raise RuntimeError("Factories session not set. Did you pass the 'session' fixture?")
        return cls._session


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base class configuring Factory Boy for the transactional session."""

    class Meta:
        abstract = True
        # Previous approach stored the session accessor directly, which
        # resulted in the wrong object being passed. Providing a callable keeps
        # Factory Boy lazy and reuses the scoped session correctly.
        sqlalchemy_session_factory = SQLAlchemySession.get
        sqlalchemy_session_persistence = "flush"
