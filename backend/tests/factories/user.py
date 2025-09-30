"""Factories for User-related models."""
"""Factory definitions for user-related models."""

from __future__ import annotations

from app.models.user import User

import factory
from tests.factories import BaseFactory


class UserFactory(BaseFactory):
    """Factory for the :class:`app.models.user.User` model.

    Attributes
    ----------
    email: factory.Sequence
        Generates unique email addresses for each instance.
    name: factory.LazyAttribute
        Derives a simple display name from the generated email.
    password_hash: factory.LazyFunction
        Placeholder value overwritten by the ``password`` hook.
    """

    class Meta:
        model = User

    id = None  # let autoincrement handle it
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.LazyAttribute(lambda o: o.email.split("@")[0].capitalize())
    password_hash = factory.LazyFunction(lambda: "")  # will be set via postgen

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set the password using the model's property for hashing.

        Parameters
        ----------
        obj: User
            Instance being built by the factory.
        create: bool
            Indicates whether the object is persisted.
        extracted: str | None
            Optional explicit password provided to the factory.
        **kwargs
            Ignored extra keyword arguments from Factory Boy.
        """
        value = extracted or "Passw0rd!"
        # Use model's setter so we test the domain logic
        obj.password = value
