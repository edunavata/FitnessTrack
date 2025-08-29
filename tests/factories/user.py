"""Factories for user-related models."""

from __future__ import annotations

import factory

from app.core.database import db
from app.models.user import User

from . import SQLAlchemyFactory, faker


class UserFactory(SQLAlchemyFactory):
    """Factory for :class:`app.models.user.User`."""

    class Meta:
        model = User
        sqlalchemy_session = db.session

    email = factory.LazyAttribute(lambda _: faker.unique.email())
    password = factory.PostGenerationMethodCall("password", "password123")

