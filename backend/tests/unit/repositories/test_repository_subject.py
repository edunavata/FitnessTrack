"""Unit tests for :mod:`app.repositories.subject`."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.models.subject import SexEnum
from app.repositories.subject import SubjectRepository
from tests.factories.subject import SubjectFactory, SubjectProfileFactory


class TestSubjectRepository:
    """Ensure ``SubjectRepository`` handles lookups and profile management."""

    def test_get_by_user_id_eagerloads_profile(self, session):
        """Fetch a subject by user id and confirm profile eager loading."""
        profile = SubjectProfileFactory()
        repo = SubjectRepository()

        result = repo.get_by_user_id(profile.subject.user_id)

        assert result is not None
        assert result.id == profile.subject_id
        # Joinedload should populate the profile relationship without extra queries
        assert result.profile is not None
        assert result.profile.id == profile.id

    def test_get_by_user_id_missing_returns_none(self, session):
        """Return ``None`` when no subject matches the supplied user id."""
        SubjectFactory()  # Ensure at least one subject exists
        repo = SubjectRepository()

        assert repo.get_by_user_id(999_999) is None

    def test_get_by_pseudonym_returns_subject(self, session):
        """Retrieve a subject by pseudonym identifier."""
        pseudonym = uuid4()
        subject = SubjectFactory(pseudonym=pseudonym)
        repo = SubjectRepository()

        fetched = repo.get_by_pseudonym(pseudonym)

        assert fetched is not None
        assert fetched.id == subject.id
        assert fetched.pseudonym == pseudonym

    def test_ensure_profile_creates_when_missing(self, session):
        """Create a profile on demand when it does not exist."""
        subject = SubjectFactory()
        repo = SubjectRepository()

        profile = repo.ensure_profile(subject.id)

        session.refresh(subject)
        assert profile.subject_id == subject.id
        assert subject.profile is not None
        assert subject.profile.id == profile.id

    def test_ensure_profile_raises_when_subject_missing(self, session):
        """Raise when attempting to ensure a profile for an unknown subject."""
        repo = SubjectRepository()

        with pytest.raises(RuntimeError):
            repo.ensure_profile(42)

    def test_update_profile_mutates_existing_record(self, session):
        """Update profile fields via repository helper and enforce validators."""
        profile = SubjectProfileFactory(height_cm=170, dominant_hand="right")
        repo = SubjectRepository()

        updated = repo.update_profile(
            profile.subject_id,
            sex=SexEnum.OTHER,
            height_cm=183,
            dominant_hand="left",
        )

        assert updated.id == profile.id
        # ``update_profile`` assigns via setattr so validators still run
        assert updated.sex == SexEnum.OTHER
        assert updated.height_cm == 183
        assert updated.dominant_hand == "left"
