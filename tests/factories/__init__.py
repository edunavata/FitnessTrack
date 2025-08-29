"""Factory Boy setup for test data generation."""

from __future__ import annotations

import factory
from faker import Faker

faker = Faker()
Faker.seed(1234)


class SQLAlchemyFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base factory for SQLAlchemy models."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"

