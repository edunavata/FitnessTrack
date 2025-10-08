"""
UserRegistrationService
=======================

Process-level service that registers a new identity:

- Creates ``User`` + ``Subject`` and links them in a single transaction.
- Supports idempotent retries keyed by the natural key (email), optionally
  with an idempotency_key hook.
- Allows post-commit side-effects via a callback.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import cast

# Guarded import for DB error handling during concurrency/idempotency races
try:  # pragma: no cover - presence depends on installed extras
    from sqlalchemy.exc import IntegrityError as _SQLAlchemyIntegrityError
except Exception:  # pragma: no cover
    _SQLAlchemyIntegrityError = None

from app.repositories.subject import SubjectRepository
from app.repositories.user import UserRepository
from app.services._shared.base import BaseService
from app.services._shared.errors import ConflictError
from app.services.identity.dto import UserPublicOut
from app.services.registration.dto import UserRegistrationIn, UserRegistrationOut

IntegrityError = cast(type[BaseException] | None, _SQLAlchemyIntegrityError)


class UserRegistrationService(BaseService):
    """
    Orchestrates the user registration process (User + Subject linkage).
    """

    def register(
        self,
        dto: UserRegistrationIn,
        *,
        on_committed: Callable[[UserRegistrationOut], None] | None = None,
    ) -> UserRegistrationOut:
        """
        Register a user and link a subject in one transaction.

        :param dto: Registration input.
        :type dto: :class:`UserRegistrationIn`
        :param on_committed: Optional callback executed **after** commit.
        :type on_committed: Callable[[UserRegistrationOut], None] | None
        :returns: Registration result payload.
        :rtype: :class:`UserRegistrationOut`
        :raises ConflictError: When ``idempotent=False`` and email already exists.
        """
        # Normalize natural key early
        norm_email = dto.email.lower().strip()

        def _perform() -> UserRegistrationOut:
            # 1) Try a fast-path idempotent read if requested
            if dto.idempotent:
                with self.ro_uow() as uow_ro:
                    user_repo_ro: UserRepository = uow_ro.users
                    subject_repo_ro: SubjectRepository = uow_ro.subjects
                    existing = user_repo_ro.get_by_email(norm_email)
                    if existing is not None:
                        subj = subject_repo_ro.get_by_user_id(existing.id)
                        if subj is None:
                            # The user exists without subject (partial state) → fix in RW txn
                            pass
                        else:
                            return UserRegistrationOut(
                                user=self._to_user_public(existing),
                                subject_id=subj.id,
                                subject_pseudonym=subj.pseudonym,
                                created=False,
                            )

            # 2) Perform RW orchestration
            try:
                with self.rw_uow() as uow:
                    user_repo_rw: UserRepository = uow.users
                    subject_repo_rw: SubjectRepository = uow.subjects

                    # Re-check existence within the RW txn
                    existing_user = user_repo_rw.get_by_email(norm_email)
                    if existing_user is not None:
                        if not dto.idempotent:
                            raise ConflictError("User", "email already in use")
                        # Ensure subject exists (idempotent repair)
                        subj = subject_repo_rw.get_by_user_id(existing_user.id)
                        if subj is None:
                            subj = subject_repo_rw.model(user_id=existing_user.id)
                            subject_repo_rw.add(subj)
                        return UserRegistrationOut(
                            user=self._to_user_public(existing_user),
                            subject_id=subj.id,
                            subject_pseudonym=subj.pseudonym,
                            created=False,
                        )

                    # Create fresh user
                    user = user_repo_rw.model(
                        email=norm_email,
                        password=dto.password,  # model setter hashes
                        username=dto.username,
                        full_name=dto.full_name,
                    )
                    user_repo_rw.add(user)

                    # Create and link subject
                    subject = subject_repo_rw.model(user_id=user.id)
                    subject_repo_rw.add(subject)

                    return UserRegistrationOut(
                        user=self._to_user_public(user),
                        subject_id=subject.id,
                        subject_pseudonym=subject.pseudonym,
                        created=True,
                    )
            except Exception as exc:
                # Handle unique races if the driver is available and idempotent is enabled
                if (
                    IntegrityError is not None
                    and isinstance(exc, IntegrityError)
                    and dto.idempotent
                ):
                    # Re-read consistent state and return as idempotent hit
                    with self.ro_uow() as uow_retry:
                        user_repo_retry: UserRepository = uow_retry.users
                        subject_repo_retry: SubjectRepository = uow_retry.subjects
                        u2 = user_repo_retry.get_by_email(norm_email)
                        if u2 is not None:
                            s2 = subject_repo_retry.get_by_user_id(u2.id)
                            if s2 is not None:
                                return UserRegistrationOut(
                                    user=self._to_user_public(u2),
                                    subject_id=s2.id,
                                    subject_pseudonym=s2.pseudonym,
                                    created=False,
                                )
                # Otherwise, bubble up (global error layer maps DB errors)
                raise

        # Use idempotency hook (no-op by default; ready for a store in the future)
        result = cast(
            UserRegistrationOut,
            self.with_idempotency(dto.idempotency_key, _perform),
        )

        # Post-commit side-effects (only after transaction succeeded)
        if callable(on_committed):
            with suppress(Exception):  # pragma: no cover - callback failure is non-fatal
                on_committed(result)

        return result

    # ------------------------------------------------------------------ #
    # Mapping
    # ------------------------------------------------------------------ #

    def _to_user_public(self, user) -> UserPublicOut:
        """
        Map ORM ``User`` to :class:`UserPublicOut`.

        :param user: ORM user instance.
        :type user: :class:`app.models.user.User`
        :returns: Public-safe DTO.
        :rtype: :class:`UserPublicOut`
        """
        return UserPublicOut(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
        )
