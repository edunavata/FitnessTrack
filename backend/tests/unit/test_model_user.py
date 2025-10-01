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

    def test_age_and_height_validation(self, session):
        u = User(email="c@example.com", username="charlie")
        u.password = "pw"
        u.age = 25
        u.height_cm = 180
        u.weight_kg = 80.5
        session.add(u)
        session.commit()
        assert u.age == 25
        assert u.height_cm == 180
        assert float(u.weight_kg) == 80.5

        with pytest.raises(ValueError):
            u.age = -1
        with pytest.raises(ValueError):
            u.height_cm = 0
        with pytest.raises(ValueError):
            u.weight_kg = -10
