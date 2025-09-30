"""Factory Boy definitions for user entities used across tests."""

from __future__ import annotations

from app.models.user import User

import factory
from tests.factories import BaseFactory


class UserFactory(BaseFactory):
    """Build persisted :class:`app.models.user.User` instances."""

    class Meta:
        model = User

    id = None  # let autoincrement handle it
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.LazyAttribute(lambda o: o.email.split("@")[0].capitalize())
    password_hash = factory.LazyFunction(lambda: "")  # will be set via postgen

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set the password using the model's property for proper hashing.

        Parameters
        ----------
        obj: app.models.user.User
            Instance being initialized by Factory Boy.
        create: bool
            Indicates whether the object was actually persisted.
        extracted: str | None
            Optional password override supplied by the factory call.
        **kwargs: dict[str, object]
            Unused additional keyword arguments from Factory Boy.
        """
        value = extracted or "Passw0rd!"
        # Use model's setter so we test the domain logic
        obj.password = value
