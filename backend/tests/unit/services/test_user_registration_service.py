import pytest
from app.repositories.subject import SubjectRepository
from app.repositories.user import UserRepository
from app.services._shared.errors import ConflictError
from app.services.registration.dto import UserRegistrationIn
from app.services.registration.service import UserRegistrationService
from tests.factories.subject import SubjectFactory
from tests.factories.user import UserFactory


class TestUserRegistrationService:
    """Validate registration process: create User+Subject and idempotency semantics."""

    @pytest.fixture()
    def service(self) -> UserRegistrationService:
        return UserRegistrationService()

    @pytest.fixture()
    def urepo(self, session) -> UserRepository:
        return UserRepository(session=session)

    @pytest.fixture()
    def srepo(self, session) -> SubjectRepository:
        return SubjectRepository(session=session)

    # -------------------------- Happy path -------------------------------- #

    def test_register_creates_user_and_subject(self, service, urepo, srepo):
        dto = UserRegistrationIn(
            email="new@example.com",
            password="StrongP@ssw0rd",
            username="newuser",
            full_name="New User",
        )
        out = service.register(dto)

        assert out.created is True
        assert out.user.email == "new@example.com"
        assert out.subject_id > 0
        assert out.subject_pseudonym is not None

        # persisted
        u = urepo.get_by_email("new@example.com")
        assert u is not None
        s = srepo.get_by_user_id(u.id)
        assert s is not None and s.id == out.subject_id

    # -------------------------- Idempotent behaviour ---------------------- #

    def test_register_idempotent_returns_existing(self, service, urepo, srepo, session):
        # Seed existing user+subject
        u = UserFactory(email="dup@example.com")
        s = SubjectFactory(user=u)
        session.flush()

        dto = UserRegistrationIn(
            email="dup@example.com",
            password="irrelevant",
            username="ignored",  # ignored in idempotent hit
            idempotent=True,
        )
        out = service.register(dto)

        assert out.created is False
        assert out.user.id == u.id
        assert out.subject_id == s.id

    def test_register_non_idempotent_conflict(self, service):
        UserFactory(email="taken@example.com")
        dto = UserRegistrationIn(
            email="taken@example.com",
            password="x",
            username="y",
            idempotent=False,
        )
        with pytest.raises(ConflictError):
            service.register(dto)

    def test_register_idempotent_repairs_missing_subject(self, service, srepo, session):
        # Seed only the user (no subject)
        u = UserFactory(email="lonely@example.com")
        session.flush()

        dto = UserRegistrationIn(
            email="  LONELY@example.com  ",  # ensure normalization
            password="x",
            username="z",
            idempotent=True,
        )
        out = service.register(dto)

        assert out.created is False  # repair path counts as idempotent hit
        s = srepo.get_by_user_id(u.id)
        assert s is not None
        assert out.subject_id == s.id

    # -------------------------- Side-effects ------------------------------ #

    def test_register_invokes_on_committed_callback(self, service):
        calls = {"n": 0}

        def _cb(res):
            calls["n"] += 1
            assert res.user.email == "cb@example.com"

        dto = UserRegistrationIn(
            email="cb@example.com",
            password="x",
            username="cbuser",
        )
        _ = service.register(dto, on_committed=_cb)
        assert calls["n"] == 1
