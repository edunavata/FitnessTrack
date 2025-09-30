"""Unit tests ensuring User model hashing, uniqueness, and timestamps."""

from __future__ import annotations

import pytest
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from tests.factories.user import UserFactory


class TestUserModel:
    """Tests for User domain logic."""

    @pytest.mark.unit
    def test_password_is_hashed_and_write_only(self, session):
        """Ensure passwords hash and stay write only.

        Arrange a user with a known raw password.
        Act by flushing the instance.
        Assert the hash differs and direct reads raise.
        """
        u = UserFactory(email="alice@example.com", password="S3cret!!!")
        session.add(u)
        session.flush()

        assert u.password_hash and u.password_hash != "S3cret!!!"

        with pytest.raises(AttributeError):
            _ = u.password

    @pytest.mark.unit
    def test_verify_password(self, session):
        """Check password verification paths.

        Arrange a user with a known password.
        Act by calling ``verify_password`` with correct and incorrect inputs.
        Assert success only for the matching password.
        """
        u = UserFactory(email="bob@example.com", password="Correct#1")
        session.add(u)
        session.flush()

        assert u.verify_password("Correct#1") is True
        assert u.verify_password("wrong") is False

    @pytest.mark.unit
    def test_email_unique(self, session):
        """Arrange two users sharing an email, flush the second, and expect an integrity error."""
        _ = UserFactory(email="dup@example.com")
        session.flush()

        # Create a second instance with the same email (must include name)
        session.add(User(email="dup@example.com", name="Dup", password_hash="x"))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_timestamps_present(self, session):
        """Populate timestamp columns via the mixin.

        Arrange a user from the factory.
        Act by flushing the session.
        Assert created and updated timestamps are present.
        """
        u = UserFactory()
        session.add(u)
        session.flush()
        assert u.created_at is not None
        assert u.updated_at is not None
