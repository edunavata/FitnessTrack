"""Unit tests for UserRepository."""

import pytest
from app.repositories.user import UserRepository
from tests.factories.user import UserFactory


class TestUserRepository:
    """Ensure ``UserRepository`` performs core persistence operations."""
    @pytest.fixture()
    def repo(self):
        return UserRepository()

    def test_create_and_get_user(self, repo, session):
        """Create a user and fetch it by email to verify retrieval."""
        u = UserFactory(email="alice@example.com", username="alice")
        session.add(u)
        session.commit()

        fetched = repo.get_by_email("alice@example.com")
        assert fetched is not None
        assert fetched.id == u.id
        assert fetched.username == "alice"

    def test_exists_by_email(self, repo, session):
        """Return existence flags for known and unknown email addresses."""
        u = UserFactory(email="bob@example.com")
        session.add(u)
        session.commit()

        assert repo.exists_by_email("bob@example.com")
        assert not repo.exists_by_email("nonexistent@example.com")

    def test_update_password(self, repo, session):
        """Update a user's password hash and verify authentication works."""
        u = UserFactory(email="c@example.com", password_hash="x")
        session.add(u)
        session.commit()

        old_hash = u.password_hash
        repo.update_password(u.id, "newpass123")
        session.commit()

        refreshed = repo.get(u.id)
        assert refreshed.password_hash != old_hash
        assert refreshed.verify_password("newpass123")

    def test_authenticate_valid_and_invalid(self, repo, session):
        """Authenticate with correct credentials and reject invalid attempts."""
        u = UserFactory(email="auth@example.com", username="authuser")
        u.password = "strongpass"
        session.add(u)
        session.commit()

        # ✅ valid
        assert repo.authenticate("auth@example.com", "strongpass") is not None
        # ❌ wrong password
        assert repo.authenticate("auth@example.com", "wrongpass") is None
        # ❌ unknown user
        assert repo.authenticate("nope@example.com", "strongpass") is None

    def test_safe_update_fields(self, repo, session):
        """Assign whitelisted fields and reject disallowed keys."""
        u = UserFactory()
        session.add(u)
        session.commit()

        updated = repo.assign_updates(u, {"username": "newname"})
        assert updated.username == "newname"

        # ❌ disallowed field (password)
        with pytest.raises(ValueError):
            repo.assign_updates(u, {"password_hash": "x"})
