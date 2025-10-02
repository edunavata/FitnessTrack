"""Factory Boy definition for :class:`app.models.user.User`."""

from __future__ import annotations

from app.models.user import User

import factory
from tests.factories import BaseFactory


class UserFactory(BaseFactory):
    """
    Build persisted :class:`app.models.user.User` instances.

    Notes
    -----
    - Indirect PII (age, height, weight, etc.) is *not* part of ``User``.
      Those attributes belong to subject-scoped tables.
    """

    class Meta:
        model = User

    id = None  # let autoincrement handle it
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    full_name = factory.LazyAttribute(lambda o: o.username.capitalize())
    password_hash = factory.LazyFunction(lambda: "")  # set via postgen

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password using model setter (ensures hashing)."""
        value = extracted or "Passw0rd!"
        obj.password = value
