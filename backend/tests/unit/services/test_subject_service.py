import pytest
from app.models.subject import Subject
from app.repositories.subject import SubjectRepository
from app.services._shared.dto import PaginationIn
from app.services._shared.errors import (
    ConflictError,
    NotFoundError,
    PreconditionFailedError,
)
from app.services.subjects.dto import (
    SubjectCreateIn,
    SubjectGetByPseudonymIn,
    SubjectLinkUserIn,
    SubjectListIn,
    SubjectUnlinkUserIn,
    SubjectUpdateProfileIn,
)
from app.services.subjects.service import SubjectService
from tests.factories.subject import SubjectFactory
from tests.factories.user import UserFactory


class TestSubjectService:
    """Validate SubjectService behaviours for Subject aggregate and its profile."""

    # -------------------------- Fixtures ---------------------------------- #

    @pytest.fixture()
    def service(self) -> SubjectService:
        return SubjectService()

    @pytest.fixture()
    def repo(self, session) -> SubjectRepository:
        return SubjectRepository(session=session)

    # -------------------------- Creation ---------------------------------- #

    def test_create_subject_without_user(self, service, repo):
        """Given no user_id, a subject is created with null linkage."""
        dto = SubjectCreateIn(user_id=None)
        result = service.create_subject(dto)

        assert result.subject.id > 0
        assert result.subject.user_id is None
        assert result.subject.pseudonym is not None

        # Ensure persisted
        got = repo.get(result.subject.id)
        assert got is not None and got.user_id is None

    def test_create_subject_with_existing_user_conflict(self, service, session):
        """When user already has a subject, creating another raises conflict."""
        s = SubjectFactory()
        session.flush()
        dto = SubjectCreateIn(user_id=s.user_id)

        with pytest.raises(ConflictError):
            service.create_subject(dto)

    # -------------------------- Linking ----------------------------------- #

    def test_link_user_happy_path(self, service, repo, session):
        """Link a user to an unlinked subject."""
        u = UserFactory()
        s = Subject()  # subject with no user
        session.add(s)
        session.flush()

        dto = SubjectLinkUserIn(subject_id=s.id, user_id=u.id)
        result = service.link_user(dto)

        assert result.subject.user_id == u.id
        got = repo.get(s.id)
        assert got is not None and got.user_id == u.id

    def test_link_user_conflict_subject_already_linked_to_other(self, service, session):
        """When subject is already linked to a different user, linking raises conflict."""
        u1 = UserFactory()
        u2 = UserFactory()
        s = SubjectFactory(user_id=u1.id)
        session.flush()

        dto = SubjectLinkUserIn(subject_id=s.id, user_id=u2.id)
        with pytest.raises(ConflictError):
            service.link_user(dto)

    def test_link_user_conflict_user_already_has_subject(self, service, session):
        """When user already has a subject, linking to another subject raises conflict."""
        u = UserFactory()
        SubjectFactory(user_id=u.id)
        s2 = SubjectFactory(user_id=None)
        session.flush()

        dto = SubjectLinkUserIn(subject_id=s2.id, user_id=u.id)
        with pytest.raises(ConflictError):
            service.link_user(dto)

    def test_link_user_etag_precondition_failed_when_mismatch(self, service, session):
        """If if_match is provided and mismatches, raise PreconditionFailedError (when ETag supported)."""
        u = UserFactory()
        s = SubjectFactory(user_id=None)
        session.flush()

        # Guard: if model does not support ETag, skip this test
        if not hasattr(s, "compute_etag"):
            pytest.skip("Subject model does not implement compute_etag(); skipping ETag test.")

        dto = SubjectLinkUserIn(subject_id=s.id, user_id=u.id, if_match="bogus")
        with pytest.raises(PreconditionFailedError):
            service.link_user(dto)

    def test_link_user_etag_matches_allows_link(self, service, repo, session):
        """When if_match equals current ETag, linking succeeds (when ETag supported)."""
        u = UserFactory()
        s = SubjectFactory(user_id=None)
        session.flush()

        if not hasattr(s, "compute_etag"):
            pytest.skip("Subject model does not implement compute_etag(); skipping ETag test.")

        good_etag = str(s.compute_etag())
        dto = SubjectLinkUserIn(subject_id=s.id, user_id=u.id, if_match=good_etag)
        out = service.link_user(dto)

        assert out.subject.user_id == u.id
        got = repo.get(s.id)
        assert got is not None and got.user_id == u.id

    # -------------------------- Unlinking --------------------------------- #

    def test_unlink_user_happy_path(self, service, repo, session):
        """Unlink user (set user_id = NULL)."""
        u = UserFactory()
        s = SubjectFactory(user_id=u.id)
        session.flush()

        dto = SubjectUnlinkUserIn(subject_id=s.id)
        out = service.unlink_user(dto)

        assert out.subject.user_id is None
        got = repo.get(s.id)
        assert got is not None and got.user_id is None

    def test_unlink_user_not_found(self, service):
        """Unlink a non-existing subject → NotFoundError."""
        dto = SubjectUnlinkUserIn(subject_id=9999)
        with pytest.raises(NotFoundError):
            service.unlink_user(dto)

    def test_unlink_user_etag_mismatch(self, service, session):
        """When if_match mismatches (and ETag supported), precondition fails."""
        u = UserFactory()
        s = SubjectFactory(user_id=u.id)
        session.flush()

        if not hasattr(s, "compute_etag"):
            pytest.skip("Subject model does not implement compute_etag(); skipping ETag test.")

        dto = SubjectUnlinkUserIn(subject_id=s.id, if_match="bogus")
        with pytest.raises(PreconditionFailedError):
            service.unlink_user(dto)

    # -------------------------- Profile update ---------------------------- #

    def test_update_profile_creates_and_updates(self, service, repo, session):
        """Ensure profile is created if missing and fields are updated."""
        s = SubjectFactory(user_id=None)
        session.flush()

        dto = SubjectUpdateProfileIn(
            subject_id=s.id,
            sex="MALE",
            birth_year=1990,
            height_cm=180,
            dominant_hand="right",
        )
        out = service.update_profile(dto)

        assert out.profile is not None
        assert (
            out.profile.sex == "SexEnum.MALE" or out.profile.sex == "MALE"
        )  # depending on __str__
        assert out.profile.birth_year == 1990
        assert out.profile.height_cm == 180
        assert out.profile.dominant_hand == "right"

        # Verify persisted
        got = repo.get(s.id)
        assert got is not None and got.profile is not None
        assert got.profile.height_cm == 180

    def test_update_profile_invalid_height_raises(self, service, session):
        """Model validators should raise on invalid values."""
        s = SubjectFactory(user_id=None)
        session.flush()

        dto = SubjectUpdateProfileIn(
            subject_id=s.id,
            height_cm=0,  # invalid
        )
        with pytest.raises(ValueError):
            service.update_profile(dto)

    def test_update_profile_etag_mismatch(self, service, session):
        """ETag precondition on profile: mismatch should fail when supported."""
        s = SubjectFactory(user_id=None)
        session.flush()

        # First, create the profile
        dto1 = SubjectUpdateProfileIn(subject_id=s.id, height_cm=170)
        _ = service.update_profile(dto1)

        # Fresh instance for ETag check
        s2 = SubjectRepository().get(s.id)
        assert s2 is not None

        if not hasattr(s2.profile, "compute_etag"):
            pytest.skip(
                "SubjectProfile model does not implement compute_etag(); skipping ETag test."
            )

        # Mismatch
        dto2 = SubjectUpdateProfileIn(subject_id=s.id, height_cm=171, if_match="bogus")
        with pytest.raises(PreconditionFailedError):
            service.update_profile(dto2)

    # -------------------------- Retrieval -------------------------------- #

    def test_get_subject_returns(self, service, session):
        """Retrieve by id returns the subject with optional profile."""
        s = SubjectFactory()
        session.flush()

        out = service.get_subject(s.id)
        assert out.subject.id == s.id
        assert out.subject.pseudonym == s.pseudonym

    def test_get_subject_not_found(self, service):
        with pytest.raises(NotFoundError):
            service.get_subject(9999)

    def test_get_by_user_id_returns(self, service, session):
        u = UserFactory()
        s = Subject(user_id=u.id)
        session.add(s)
        session.flush()

        out = service.get_by_user_id(u.id)
        assert out.subject.id == s.id
        assert out.subject.user_id == u.id

    def test_get_by_pseudonym_returns(self, service, session):
        s = SubjectFactory()
        session.flush()

        out = service.get_by_pseudonym(SubjectGetByPseudonymIn(pseudonym=s.pseudonym))
        assert out.subject.id == s.id

    # -------------------------- Listing ----------------------------------- #

    def test_list_subjects_basic_pagination(self, service, session):
        """List returns items and meta based on pagination in/out."""
        # Seed multiple
        SubjectFactory()
        SubjectFactory()
        SubjectFactory()
        session.flush()

        dto = SubjectListIn(
            pagination=PaginationIn(page=1, limit=2, sort=["id"]),
            filters=None,
            with_total=True,
        )
        result = service.list_subjects(dto)

        assert len(result.items) == 2
        assert result.meta.page == 1
        assert result.meta.limit == 2
        assert result.meta.total >= 3
        assert result.meta.has_next is True
