"""Unit tests covering the :class:`app.models.user.User` model behavior."""

from __future__ import annotations

import pytest
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from tests.factories.user import UserFactory


class TestUserModel:
    """Validate password hashing, uniqueness, and timestamps for ``User``."""

    @pytest.mark.unit
    def test_password_is_hashed_and_write_only(self, session):
        """Arrange a user, set a password, and ensure hashing hides plaintext.

        The factory assigns a password before flush. The test flushes to trigger
        the hashing logic and asserts the hash differs from the input while
        accessing ``password`` raises :class:`AttributeError`.
        """
        u = UserFactory(email="alice@example.com", password="S3cret!!!")
        session.add(u)
        session.flush()

        assert u.password_hash and u.password_hash != "S3cret!!!"

        with pytest.raises(AttributeError):
            _ = u.password

    @pytest.mark.unit
    def test_verify_password(self, session):
        """Arrange a persisted user and verify correct and incorrect secrets.

        After flushing the factory-created user, the test calls
        :meth:`User.verify_password` with the expected password and an invalid
        value to assert the method returns ``True`` and ``False`` respectively.
        """
        u = UserFactory(email="bob@example.com", password="Correct#1")
        session.add(u)
        session.flush()

        assert u.verify_password("Correct#1") is True
        assert u.verify_password("wrong") is False

    @pytest.mark.unit
    def test_email_unique(self, session):
        """Arrange two users with same email to assert unique constraint.

        The factory creates the first user. The test inserts a second ``User``
        with the same email and expects :class:`IntegrityError` during
        ``session.flush()`` to confirm the database enforces uniqueness.
        """
        _ = UserFactory(email="dup@example.com")
        session.flush()

        # Create a second instance with the same email (must include name)
        session.add(User(email="dup@example.com", name="Dup", password_hash="x"))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_timestamps_present(self, session):
        """Arrange a user instance and confirm timestamp mixin defaults.

        After flushing the user to the database, ``created_at`` and
        ``updated_at`` should both be populated, demonstrating the mixin column
        defaults work as expected.
        """
        u = UserFactory()
        session.add(u)
        session.flush()
        assert u.created_at is not None
        assert u.updated_at is not None
