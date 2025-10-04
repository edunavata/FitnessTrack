"""Subject repository implementing persistence-only operations.

This module provides :class:`SubjectRepository`, a thin persistence wrapper
around :class:`~app.repositories.base.BaseRepository`. It keeps data access
concerns isolated from business logic and transaction orchestration while
documenting eager-loading and sorting conventions for :class:`Subject`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import InstrumentedAttribute, joinedload

from app.models.subject import SexEnum, Subject, SubjectProfile
from app.repositories.base import BaseRepository


class SubjectRepository(BaseRepository[Subject]):
    """Persist :class:`Subject` aggregates and expose profile helpers.

    The repository provides deterministic sorting, optional equality filtering
    and lean eager loading for the profile relationship. Services handle
    transactions and broader orchestration.
    """

    model = Subject

    # ---- Sorting whitelist --------------------------------------------------
    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        """
        Return safe, indexed or stable columns allowed for sorting.

        :returns: Public key → ORM attribute mapping.
        :rtype: Mapping[str, InstrumentedAttribute]
        """
        return {
            "id": self.model.id,
            "created_at": self.model.created_at,
            "updated_at": self.model.updated_at,
            "user_id": self.model.user_id,
            "pseudonym": self.model.pseudonym,
        }

    # ---- Filter whitelist (equality-only) -----------------------------------
    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        """
        Restrict equality filters to a known-safe subset.

        :returns: Public key → ORM attribute mapping, or ``None`` for legacy mode.
        :rtype: Mapping[str, InstrumentedAttribute] | None
        """
        return {
            "id": self.model.id,
            "user_id": self.model.user_id,
            "pseudonym": self.model.pseudonym,
        }

    # ---- Updatable whitelist -------------------------------------------------
    def _updatable_fields(self) -> set[str]:
        """
        Allow-list of fields that can be mass-assigned via ``update()`` helpers.

        We intentionally keep this **strict** to avoid mass-assignment bugs.
        Profile fields are mutated via dedicated helpers (see ``update_profile``).

        :returns: Set of field names.
        :rtype: set[str]
        """
        return {
            # Only top-level Subject scalar columns:
            "user_id",
            # NOTE: Do not allow 'pseudonym' to be mass-assigned unless you need it.
        }

    # ---- Default eager loading ----------------------------------------------
    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        """
        Attach sensible eager-loading to reduce N+1 without over-fetching.

        * ``profile`` is 1:1 → ``joinedload`` is typically fine for listings.
        * Light read-only shortcuts can use ``selectinload``.
        """
        return stmt.options(
            joinedload(self.model.profile),  # 1:1 ⇒ joinedload
            # Light collections could be added when needed:
            # selectinload(self.model.saved_routines),
            # selectinload(self.model.owned_routines),
        )

    # ------------------------------ Lookups -----------------------------------
    def get_by_user_id(self, user_id: int) -> Subject | None:
        """
        Find a subject by its ``user_id``.

        :param user_id: User identifier linked to the subject.
        :type user_id: int
        :returns: Subject or ``None``.
        :rtype: Subject | None
        """
        stmt: Select[Any] = select(self.model).where(self.model.user_id == user_id)
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(Subject | None, result)

    def get_by_pseudonym(self, pseudonym: UUID) -> Subject | None:
        """
        Find a subject by its pseudonymous UUID.

        :param pseudonym: Pseudonymous stable UUID.
        :type pseudonym: :class:`uuid.UUID`
        :returns: Subject or ``None``.
        :rtype: Subject | None
        """
        stmt: Select[Any] = select(self.model).where(self.model.pseudonym == pseudonym)
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(Subject | None, result)

    # ---------------------------- Profile helpers -----------------------------
    def ensure_profile(self, subject_id: int) -> SubjectProfile:
        """
        Ensure the subject has a profile row, creating it if missing.

        :param subject_id: Subject primary key.
        :type subject_id: int
        :returns: Existing or newly created ``SubjectProfile``.
        :rtype: :class:`app.models.subject.SubjectProfile`
        :raises RuntimeError: If subject does not exist.
        """
        subject = self.get(subject_id)
        if subject is None:
            raise RuntimeError("Subject not found.")

        profile: SubjectProfile | None = subject.profile
        if profile is None:
            profile = SubjectProfile(subject_id=subject.id)
            subject.profile = profile
            self.flush()

        # mypy now knows ``profile`` is a SubjectProfile instance
        return profile

    def update_profile(
        self,
        subject_id: int,
        *,
        sex: SexEnum | str | None = None,
        birth_year: int | None = None,
        height_cm: int | None = None,
        dominant_hand: str | None = None,
        flush: bool = True,
    ) -> SubjectProfile:
        """
        Update (or create) the 1:1 profile using model validators.

        This uses attribute assignment to trigger SQLAlchemy ``@validates``
        decorators defined on the mapped class.

        :param subject_id: Subject primary key.
        :type subject_id: int
        :param sex: Optional sex enum value.
        :type sex: SexEnum | str | None
        :param birth_year: Optional birth year.
        :type birth_year: int | None
        :param height_cm: Optional height in centimeters.
        :type height_cm: int | None
        :param dominant_hand: Optional dominant hand.
        :type dominant_hand: str | None
        :param flush: Whether to call ``session.flush()`` after mutation.
        :type flush: bool
        :returns: The mutated ``SubjectProfile``.
        :rtype: :class:`app.models.subject.SubjectProfile`
        """
        profile = self.ensure_profile(subject_id)
        # Assign via setattr to trigger validators
        if sex is not None:
            profile.sex = SexEnum(sex) if isinstance(sex, str) else sex
        if birth_year is not None:
            profile.birth_year = birth_year
        if height_cm is not None:
            profile.height_cm = height_cm
        if dominant_hand is not None:
            profile.dominant_hand = dominant_hand

        if flush:
            self.flush()
        return profile
