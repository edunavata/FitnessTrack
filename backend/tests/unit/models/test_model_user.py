"""Tests for the User model."""

from __future__ import annotations

import pytest
from app.models.user import User
from sqlalchemy.exc import IntegrityError


class TestUser:
    def test_password_hashing(self, session):
        u = User(email="Test@Example.com", username="tester")
        u.password = "secret123"
        session.add(u)
        session.commit()
        assert u.verify_password("secret123") is True
        assert u.verify_password("wrong") is False

    def test_password_is_write_only(self):
        u = User(email="a@example.com", username="u1")
        u.password = "x"
        with pytest.raises(AttributeError):
            _ = u.password

    def test_email_normalized_and_unique(self, session):
        u1 = User(email="Alice@Example.com", username="alice")
        u1.password = "pw"
        session.add(u1)
        session.commit()
        assert u1.email == "alice@example.com"

        u2 = User(email="alice@example.com", username="alice2")
        u2.password = "pw"
        session.add(u2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_username_unique(self, session):
        u1 = User(email="b1@example.com", username="bob")
        u1.password = "pw"
        session.add(u1)
        session.commit()

        u2 = User(email="b2@example.com", username="bob")
        u2.password = "pw"
        session.add(u2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_no_indirect_pii_fields(self):
        # User must not include indirect PII fields anymore
        u = User(email="c@example.com", username="charlie")
        assert not hasattr(u, "age")
        assert not hasattr(u, "height_cm")
        assert not hasattr(u, "weight_kg")

    def test_basic_validations(self, session):
        # email required
        with pytest.raises(ValueError):
            User(email="", username="u")._normalize_email("email", "")
        # username required
        with pytest.raises(ValueError):
            User(email="x@example.com", username=" ")._normalize_username("username", " ")
