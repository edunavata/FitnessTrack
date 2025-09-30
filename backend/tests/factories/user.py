"""Factories for User-related models."""

from __future__ import annotations

from app.models.user import User

import factory
from tests.factories import BaseFactory


class UserFactory(BaseFactory):
    """Factory for the `User` model."""

    class Meta:
        model = User

    id = None  # let autoincrement handle it
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.LazyAttribute(lambda o: o.email.split("@")[0].capitalize())
    password_hash = factory.LazyFunction(lambda: "")  # will be set via postgen

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password using the model's property for proper hashing."""
        value = extracted or "Passw0rd!"
        # Use model's setter so we test the domain logic
        obj.password = value
