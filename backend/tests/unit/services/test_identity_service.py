import pytest
from app.repositories.user import UserRepository
from app.services._shared.errors import (
    ConflictError,
    NotFoundError,
    ServiceError,
)
from app.services.identity.dto import (
    UserAuthIn,
    UserPasswordChangeIn,
    UserRegisterIn,
    UserUpdateIn,
)
from app.services.identity.service import IdentityService
from tests.factories.user import UserFactory


class TestIdentityService:
    """Validate IdentityService behaviours for the User aggregate."""

    @pytest.fixture()
    def service(self) -> IdentityService:
        """Return a fresh service instance per test."""
        return IdentityService()

    @pytest.fixture()
    def repo(self, session) -> UserRepository:
        """Provide repository bound to the current transactional session."""
        return UserRepository(session=session)

    # --------------------------------------------------------------------- #
    # Registration
    # --------------------------------------------------------------------- #

    def test_register_user_creates_new_user(self, service, repo):
        """Given valid data, a new user is registered."""
        dto = UserRegisterIn(
            email="new@example.com",
            password="password123",
            username="newuser",
            full_name="John Doe",
        )

        result = service.register_user(dto)

        assert result.email == "new@example.com"
        assert result.username == "newuser"

        stored = repo.get_by_email("new@example.com")
        assert stored is not None
        assert stored.verify_password("password123")

    def test_register_user_raises_conflict_when_email_exists(self, service):
        """Given an existing email, registration raises ConflictError."""
        UserFactory(email="dup@example.com")
        dto = UserRegisterIn(
            email="dup@example.com",
            password="otherpass",
            username="another",
        )

        with pytest.raises(ConflictError):
            service.register_user(dto)

    # --------------------------------------------------------------------- #
    # Authentication
    # --------------------------------------------------------------------- #

    def test_authenticate_returns_user_on_valid_credentials(self, service, session):
        """Given valid credentials, authentication returns the user payload."""
        user = UserFactory(password="validpass")
        session.flush()
        dto = UserAuthIn(email=user.email, password="validpass")

        result = service.authenticate(dto)

        assert result.id == user.id
        assert result.email == user.email
        assert result.username == user.username

    def test_authenticate_raises_on_invalid_credentials(self, service, session):
        """Given wrong password, authentication raises ServiceError."""
        user = UserFactory(password="rightpass")
        session.flush()
        dto = UserAuthIn(email=user.email, password="wrongpass")

        with pytest.raises(ServiceError, match="Invalid credentials"):
            service.authenticate(dto)

    # --------------------------------------------------------------------- #
    # Retrieval
    # --------------------------------------------------------------------- #

    def test_get_user_returns_correct_user(self, service, session):
        """Given an existing user, it can be retrieved by ID."""
        user = UserFactory()
        session.flush()
        result = service.get_user(user.id)

        assert result.id == user.id
        assert result.email == user.email
        assert result.username == user.username

    def test_get_user_raises_when_not_found(self, service):
        """Given a non-existing user, raises NotFoundError."""
        with pytest.raises(NotFoundError):
            service.get_user(9999)

    # --------------------------------------------------------------------- #
    # Update PII
    # --------------------------------------------------------------------- #

    def test_update_user_modifies_fields(self, service, repo):
        """Given valid PII updates, the user is updated successfully."""
        user = UserFactory(email="old@example.com", username="oldname")
        dto = UserUpdateIn(email="updated@example.com", username="newname")

        result = service.update_user(user.id, dto)

        assert result.email == "updated@example.com"
        assert result.username == "newname"

        updated = repo.get(user.id)
        assert updated.email == "updated@example.com"
        assert updated.username == "newname"

    def test_update_user_raises_not_found(self, service):
        """Given a non-existing user, raises NotFoundError."""
        dto = UserUpdateIn(email="nonexistent@example.com")
        with pytest.raises(NotFoundError):
            service.update_user(9999, dto)

    # --------------------------------------------------------------------- #
    # Password management
    # --------------------------------------------------------------------- #

    def test_change_password_updates_hash(self, service, repo):
        """Given valid old password, the hash is updated."""
        user = UserFactory(password="oldpass")

        dto = UserPasswordChangeIn(
            user_id=user.id,
            old_password="oldpass",
            new_password="newpass123",
        )
        service.change_password(dto)

        updated = repo.get(user.id)
        assert updated.verify_password("newpass123")

    def test_change_password_raises_if_old_password_incorrect(self, service):
        """Given incorrect old password, raises ServiceError."""
        user = UserFactory(password="correctpass")

        dto = UserPasswordChangeIn(
            user_id=user.id,
            old_password="wrongpass",
            new_password="newpass",
        )

        with pytest.raises(ServiceError, match="Old password is incorrect"):
            service.change_password(dto)
