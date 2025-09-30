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
        """Arrange a user with a known password, flush, then assert hashing and access protections hold."""
        u = UserFactory(email="alice@example.com", password="S3cret!!!")
        session.add(u)
        session.flush()

        assert u.password_hash and u.password_hash != "S3cret!!!"

        with pytest.raises(AttributeError):
            _ = u.password

    @pytest.mark.unit
    def test_verify_password(self, session):
        """Arrange a user with a password, invoke ``verify_password``, and assert correct and incorrect inputs behave as expected."""
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
        """Arrange a user, flush it, and assert timestamp columns populate via the mixin defaults."""
        u = UserFactory()
        session.add(u)
        session.flush()
        assert u.created_at is not None
        assert u.updated_at is not None
