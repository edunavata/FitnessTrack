"""
SubjectService
==============

Aggregate application service for managing the ``Subject`` aggregate:

- Create subject and optional initial link to ``User``.
- Link/unlink a ``User`` while enforcing invariants.
- Manage 1:1 ``SubjectProfile`` (ensure + update).
- Retrieve by id, user_id, pseudonym and list with pagination.

Notes
-----
- This service is framework-agnostic; it never returns HTTP concerns.
- Errors are expressed via domain exceptions from ``_shared.errors``.
- Read operations use ``ro_uow()``; write operations use ``rw_uow()``.
"""

from __future__ import annotations

from typing import Any

from app.repositories.subject import SubjectRepository
from app.services._shared.base import BaseService
from app.services._shared.dto import PageMeta
from app.services._shared.errors import ConflictError, NotFoundError, PreconditionFailedError
from app.services.subjects.dto import (
    SubjectCreateIn,
    SubjectGetByPseudonymIn,
    SubjectLinkUserIn,
    SubjectListIn,
    SubjectListOut,
    SubjectProfileOut,
    SubjectPublicOut,
    SubjectUnlinkUserIn,
    SubjectUpdateProfileIn,
    SubjectWithProfileOut,
)
from psycopg2 import IntegrityError


class SubjectService(BaseService):
    """
    Application service for the ``Subject`` aggregate.

    Responsibilities
    ----------------
    - Create and retrieve subjects.
    - Enforce 1:1 link between subject and user.
    - Ensure and update subject profile.
    - Provide paginated listings with safe sorting/filtering.
    """

    # --------------------------------------------------------------------- #
    # Creation
    # --------------------------------------------------------------------- #

    def create_subject(self, dto: SubjectCreateIn) -> SubjectWithProfileOut:
        """
        Create a subject (optionally linked to a user).

        :param dto: Creation parameters.
        :type dto: :class:`SubjectCreateIn`
        :returns: Subject with optional profile (typically ``None`` just created).
        :rtype: :class:`SubjectWithProfileOut`
        :raises ConflictError: If the given user already has a subject.
        """
        self.ensure_owner(actor_id=self.ctx.actor_id, owner_id=dto.user_id)
        with self.rw_uow() as uow:
            repo: SubjectRepository = uow.subjects

            if dto.user_id is not None:
                existing = repo.get_by_user_id(dto.user_id)
                if existing is not None:
                    raise ConflictError("Subject", "user already linked to a subject")

            try:
                subject = repo.model(user_id=dto.user_id)
                repo.add(subject)
            except IntegrityError as exc:
                # Colisión con UNIQUE(subjects.user_id) o FK
                raise ConflictError("Subject", "user already linked to a subject") from exc
            # no explicit commit; UoW handles on context exit
            return self._to_subject_with_profile(subject)

    # --------------------------------------------------------------------- #
    # Linking / Unlinking
    # --------------------------------------------------------------------- #

    def link_user(self, dto: SubjectLinkUserIn) -> SubjectWithProfileOut:
        """
        Link a subject to a user, enforcing 1:1 invariant.

        :param dto: Link parameters including ETag.
        :type dto: :class:`SubjectLinkUserIn`
        :returns: Updated subject with profile.
        :rtype: :class:`SubjectWithProfileOut`
        :raises NotFoundError: If subject does not exist.
        :raises ConflictError: If user is already linked to a different subject,
                               or the subject is linked to another user.
        :raises PreconditionFailedError: When ETag ``if_match`` mismatches.
        """
        self.ensure_owner(actor_id=self.ctx.subject_id, owner_id=dto.subject_id)
        with self.rw_uow() as uow:
            repo: SubjectRepository = uow.subjects
            subject = repo.get_for_update(dto.subject_id)
            if subject is None:
                raise NotFoundError("Subject", dto.subject_id)

            # ETag precondition on the subject if provided and supported
            if dto.if_match:
                current_etag = self._maybe_etag(subject)
                self.ensure_if_match(dto.if_match, current_etag)

            # If the subject is already linked to a different user → conflict
            if subject.user_id is not None and subject.user_id != dto.user_id:
                raise ConflictError("Subject", "subject already linked to another user")

            # If this user is already linked to another subject → conflict
            other = repo.get_by_user_id(dto.user_id)
            if other is not None and other.id != subject.id:
                raise ConflictError("Subject", "user already linked to a subject")

            user = uow.users.get(dto.user_id)
            if user is None:
                raise NotFoundError("User", dto.user_id)

            # avoid TOCTOU
            try:
                repo.update(subject, user_id=dto.user_id)
            except IntegrityError as exc:
                # UNIQUE(subjects.user_id) o FK violation → traducir a dominio
                raise ConflictError("Subject", "user already linked to a subject") from exc
            return self._to_subject_with_profile(subject)

    def unlink_user(self, dto: SubjectUnlinkUserIn) -> SubjectWithProfileOut:
        """
        Unlink the subject from its user (set ``user_id = NULL``).

        :param dto: Unlink parameters with optional ETag.
        :type dto: :class:`SubjectUnlinkUserIn`
        :returns: Updated subject with profile.
        :rtype: :class:`SubjectWithProfileOut`
        :raises NotFoundError: If subject does not exist.
        :raises PreconditionFailedError: When ETag mismatches.
        """
        self.ensure_owner(actor_id=self.ctx.subject_id, owner_id=dto.subject_id)
        with self.rw_uow() as uow:
            repo: SubjectRepository = uow.subjects
            subject = repo.get_for_update(dto.subject_id)
            if subject is None:
                raise NotFoundError("Subject", dto.subject_id)

            compute_etag = getattr(subject, "compute_etag", None)
            if dto.if_match and callable(compute_etag):
                current_etag = str(compute_etag())
                self.ensure_if_match(dto.if_match, current_etag)

            repo.update(subject, user_id=None)
            return self._to_subject_with_profile(subject)

    # --------------------------------------------------------------------- #
    # Profile management
    # --------------------------------------------------------------------- #

    def update_profile(self, dto: SubjectUpdateProfileIn) -> SubjectWithProfileOut:
        """
        Update the 1:1 profile (create if missing) with optimistic concurrency.

        :param dto: Profile fields and optional ETag.
        :type dto: :class:`SubjectUpdateProfileIn`
        :returns: Subject with updated profile.
        :rtype: :class:`SubjectWithProfileOut`
        :raises NotFoundError: If subject does not exist.
        :raises PreconditionFailedError: If ``if_match`` provided and does not match.
        """
        self.ensure_owner(actor_id=self.ctx.subject_id, owner_id=dto.subject_id)
        with self.rw_uow() as uow:
            repo: SubjectRepository = uow.subjects
            subject = repo.get_for_update(dto.subject_id)
            if subject is None:
                raise NotFoundError("Subject", dto.subject_id)

            # ETag logic: if client provided if_match, we require an existing profile
            # and validate its ETag when supported.
            existing_profile = subject.profile
            if dto.if_match:
                if existing_profile is None:
                    raise PreconditionFailedError("Precondition failed (profile missing)")
                compute_etag = getattr(existing_profile, "compute_etag", None)
                if callable(compute_etag):
                    current = str(compute_etag())
                    self.ensure_if_match(dto.if_match, current)

            # Apply mutation (ensure_profile will create when missing)
            repo.update_profile(
                subject.id,
                sex=dto.sex,
                birth_year=dto.birth_year,
                height_cm=dto.height_cm,
                dominant_hand=dto.dominant_hand,
                flush=True,
            )
            # Return fresh composed output
            return self._to_subject_with_profile(subject)

    # --------------------------------------------------------------------- #
    # Retrieval
    # --------------------------------------------------------------------- #

    def get_subject(self, subject_id: int) -> SubjectWithProfileOut:
        """
        Retrieve a subject by identifier.

        :param subject_id: Subject identifier.
        :type subject_id: int
        :returns: Subject with optional profile.
        :rtype: :class:`SubjectWithProfileOut`
        :raises NotFoundError: If subject does not exist.
        """
        with self.ro_uow() as uow:
            repo: SubjectRepository = uow.subjects
            subject = repo.get(subject_id)
            if subject is None:
                raise NotFoundError("Subject", subject_id)
            return self._to_subject_with_profile(subject)

    def get_by_user_id(self, user_id: int) -> SubjectWithProfileOut:
        """
        Retrieve a subject by its linked ``user_id``.

        :param user_id: User identifier.
        :type user_id: int
        :returns: Subject with optional profile.
        :rtype: :class:`SubjectWithProfileOut`
        :raises NotFoundError: If not found.
        """
        with self.ro_uow() as uow:
            repo: SubjectRepository = uow.subjects
            subject = repo.get_by_user_id(user_id)
            if subject is None:
                raise NotFoundError("Subject", user_id)
            return self._to_subject_with_profile(subject)

    def get_by_pseudonym(self, dto: SubjectGetByPseudonymIn) -> SubjectWithProfileOut:
        """
        Retrieve a subject by pseudonymous UUID.

        :param dto: Pseudonym lookup DTO.
        :type dto: :class:`SubjectGetByPseudonymIn`
        :returns: Subject with optional profile.
        :rtype: :class:`SubjectWithProfileOut`
        :raises NotFoundError: If not found.
        """
        with self.ro_uow() as uow:
            repo: SubjectRepository = uow.subjects
            subject = repo.get_by_pseudonym(dto.pseudonym)
            if subject is None:
                raise NotFoundError("Subject", str(dto.pseudonym))
            return self._to_subject_with_profile(subject)

    # --------------------------------------------------------------------- #
    # Listing
    # --------------------------------------------------------------------- #

    def list_subjects(self, dto: SubjectListIn) -> SubjectListOut:
        """
        List subjects with pagination, filters and safe sorting.

        :param dto: Listing input with pagination and filters.
        :type dto: :class:`SubjectListIn`
        :returns: Paginated list of subjects.
        :rtype: :class:`SubjectListOut`
        """
        with self.ro_uow() as uow:
            repo: SubjectRepository = uow.subjects

            pagination = self.ensure_pagination(
                page=dto.pagination.page,
                limit=dto.pagination.limit,
                sort=dto.pagination.sort,
            )

            page = repo.paginate(
                pagination,
                filters=dto.filters or None,
                with_total=dto.with_total,
            )

            items = [self._to_subject_with_profile(s) for s in page.items]
            meta = PageMeta(
                page=page.page,
                limit=page.limit,
                total=page.total,
                has_prev=page.page > 1,
                has_next=(page.page * page.limit) < page.total,
            )
            return SubjectListOut(items=items, meta=meta)

    # --------------------------------------------------------------------- #
    # Mapping helpers
    # --------------------------------------------------------------------- #

    def _maybe_etag(self, obj: Any) -> str | None:
        """
        Return an ETag computed by the domain object when supported.

        :param obj: Domain entity instance.
        :type obj: Any
        :returns: ETag or ``None``.
        :rtype: str | None
        """
        if obj is None:
            return None
        compute = getattr(obj, "compute_etag", None)
        if callable(compute):
            try:
                return str(compute())
            except Exception:
                return None
        return None

    def _to_subject_public(self, subject) -> SubjectPublicOut:
        """
        Map ORM ``Subject`` to :class:`SubjectPublicOut`.

        :param subject: ORM subject instance.
        :type subject: :class:`app.models.subject.Subject`
        :returns: Public-safe DTO.
        :rtype: :class:`SubjectPublicOut`
        """
        return SubjectPublicOut(
            id=subject.id,
            user_id=subject.user_id,
            pseudonym=subject.pseudonym,
            created_at=subject.created_at,
            updated_at=subject.updated_at,
            etag=self._maybe_etag(subject),
        )

    def _to_profile_out(self, profile) -> SubjectProfileOut | None:
        """
        Map ORM ``SubjectProfile`` to :class:`SubjectProfileOut`.

        :param profile: ORM profile instance or ``None``.
        :type profile: :class:`app.models.subject.SubjectProfile` | None
        :returns: Profile DTO or ``None``.
        :rtype: :class:`SubjectProfileOut` | None
        """
        if profile is None:
            return None
        return SubjectProfileOut(
            sex=str(profile.sex) if profile.sex is not None else None,
            birth_year=profile.birth_year,
            height_cm=profile.height_cm,
            dominant_hand=profile.dominant_hand,
            etag=self._maybe_etag(profile),
        )

    def _to_subject_with_profile(self, subject) -> SubjectWithProfileOut:
        """
        Compose subject and its (optional) profile.

        :param subject: ORM subject instance.
        :type subject: :class:`app.models.subject.Subject`
        :returns: Composed subject DTO.
        :rtype: :class:`SubjectWithProfileOut`
        """
        return SubjectWithProfileOut(
            subject=self._to_subject_public(subject),
            profile=self._to_profile_out(subject.profile),
        )
