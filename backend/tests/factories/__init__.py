# backend/tests/factories/__init__.py
from __future__ import annotations

import factory


class SQLAlchemySession:
    _session = None

    @classmethod
    def set(cls, session):
        cls._session = session

    @classmethod
    def get(cls):
        if cls._session is None:
            raise RuntimeError("Factories session not set. Did you pass the 'session' fixture?")
        return cls._session


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        # ❌ Antes:
        # sqlalchemy_session = SQLAlchemySession.get
        # ✅ Después (pasar *callable*):
        sqlalchemy_session_factory = SQLAlchemySession.get
        sqlalchemy_session_persistence = "flush"
