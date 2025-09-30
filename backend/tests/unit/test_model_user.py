"""Unit tests for the `User` model."""

from __future__ import annotations

import pytest
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from tests.factories.user import UserFactory


class TestUserModel:
    """Tests for User domain logic."""

    @pytest.mark.unit
    def test_password_is_hashed_and_write_only(self, session):
        """Password setter should hash and disallow reading."""
        u = UserFactory(email="alice@example.com", password="S3cret!!!")
        session.add(u)
        session.flush()

        assert u.password_hash and u.password_hash != "S3cret!!!"

        with pytest.raises(AttributeError):
            _ = u.password

    @pytest.mark.unit
    def test_verify_password(self, session):
        """verify_password should return True for correct password."""
        u = UserFactory(email="bob@example.com", password="Correct#1")
        session.add(u)
        session.flush()

        assert u.verify_password("Correct#1") is True
        assert u.verify_password("wrong") is False

    @pytest.mark.unit
    def test_email_unique(self, session):
        """Unique constraint on email should be enforced."""
        _ = UserFactory(email="dup@example.com")
        session.flush()

        # Create a second instance with the same email (must include name)
        session.add(User(email="dup@example.com", name="Dup", password_hash="x"))
        with pytest.raises(IntegrityError):
            session.flush()

    @pytest.mark.unit
    def test_timestamps_present(self, session):
        """created_at/updated_at should be filled by mixin defaults."""
        u = UserFactory()
        session.add(u)
        session.flush()
        assert u.created_at is not None
        assert u.updated_at is not None
