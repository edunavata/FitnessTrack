"""
IdentityService
===============

Aggregate service responsible for managing the `User` aggregate:
- Direct PII (email, username, full_name)
- Password lifecycle
- Authentication (verification only, no token issuance)
"""

from __future__ import annotations

from typing import Any

from app.repositories.user import UserRepository
from app.services._shared.base import BaseService
from app.services._shared.errors import (
    ConflictError,
    NotFoundError,
    PreconditionFailedError,
    ServiceError,
    violates,
)
from app.services.identity.dto import (
    UserAuthIn,
    UserAuthOut,
    UserPasswordChangeIn,
    UserPublicOut,
    UserRegisterIn,
    UserUpdateIn,
)
from sqlalchemy.exc import IntegrityError


class IdentityService(BaseService):
    """
    Application service for the `User` aggregate.

    Responsibilities
    ----------------
    - Register users ensuring email uniqueness.
    - Authenticate credentials.
    - Retrieve and update user PII safely.
    - Manage password lifecycle.
    """

    # --------------------------------------------------------------------- #
    # Registration
    # --------------------------------------------------------------------- #

    def register_user(self, dto: UserRegisterIn) -> UserPublicOut:
        """
        Register a new user.

        :param dto: User registration input DTO.
        :type dto: UserRegisterIn
        :returns: Public-safe user DTO.
        :rtype: UserPublicOut
        """

        with self.rw_uow() as uow:
            repo: UserRepository = uow.users

            if repo.exists_by_email(dto.email):
                raise ConflictError("User", "email already in use")

            try:
                user = repo.model(
                    email=dto.email,  # model hashes via setter
                    password=dto.password,
                    username=dto.username,
                    full_name=dto.full_name,
                )
                repo.add(user)
            except IntegrityError as exc:
                # Map by constraint name for precise message if you want
                if violates(exc, "uq_users_email"):  # name your constraints!
                    raise ConflictError("User", "email already in use") from exc
                if violates(exc, "uq_users_username"):
                    raise ConflictError("User", "username already in use") from exc
                raise  # unknown integrity error -> bubble up

            return UserPublicOut(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
            )

    # --------------------------------------------------------------------- #
    # Authentication
    # --------------------------------------------------------------------- #

    def authenticate(self, dto: UserAuthIn) -> UserAuthOut:
        """
        Authenticate a user by email and password.

        :param dto: Authentication input DTO.
        :type dto: UserAuthIn
        :returns: Authenticated user payload.
        :rtype: UserAuthOut
        :raises ServiceError: When credentials are invalid.
        """

        with self.ro_uow() as uow:
            repo: UserRepository = uow.users
            user = repo.authenticate(dto.email, dto.password)
            if user is None:
                raise ServiceError("Invalid credentials")

            return UserAuthOut(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
            )

    # --------------------------------------------------------------------- #
    # Retrieval
    # --------------------------------------------------------------------- #

    def get_user(self, user_id: int) -> UserPublicOut:
        """
        Retrieve a user by identifier.

        :param user_id: User primary key.
        :type user_id: int
        :returns: Public-safe user DTO.
        :rtype: UserPublicOut
        :raises NotFoundError: If user does not exist.
        """

        with self.ro_uow() as uow:
            repo: UserRepository = uow.users
            user = repo.get(user_id)
            if user is None:
                raise NotFoundError("User", user_id)

            return UserPublicOut(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
            )

    # --------------------------------------------------------------------- #
    # Update PII
    # --------------------------------------------------------------------- #

    def update_user(self, user_id: int, dto: UserUpdateIn) -> UserPublicOut:
        """
        Update user PII fields (email, username, full_name).

        :param user_id: User identifier.
        :type user_id: int
        :param dto: Input DTO containing new values.
        :type dto: UserUpdateIn
        :returns: Updated user DTO.
        :rtype: UserPublicOut
        :raises PreconditionFailedError: When ETag mismatch.
        :raises NotFoundError: When user not found.
        """

        with self.rw_uow() as uow:
            repo: UserRepository = uow.users
            user = repo.get_for_update(user_id)
            if user is None:
                raise NotFoundError("User", user_id)

            if dto.if_match:
                current_etag = user.compute_etag()
                if dto.if_match != current_etag:
                    raise PreconditionFailedError()

            updates: dict[str, Any] = {
                k: v
                for k, v in {
                    "email": dto.email,
                    "username": dto.username,
                    "full_name": dto.full_name,
                }.items()
                if v is not None
            }

            try:
                uow.users.update(user, **updates)  # dispara validaciones del modelo
            except IntegrityError as exc:
                # Map by constraint name for precise message if you want
                if violates(exc, "uq_users_email"):  # name your constraints!
                    raise ConflictError("User", "email already in use") from exc
                if violates(exc, "uq_users_username"):
                    raise ConflictError("User", "username already in use") from exc
                raise  # unknown integrity error -> bubble up

            return UserPublicOut(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
            )

    # --------------------------------------------------------------------- #
    # Password management
    # --------------------------------------------------------------------- #

    def change_password(self, dto: UserPasswordChangeIn) -> None:
        """
        Change a user's password after verifying the old one.

        :param dto: Input DTO containing old and new passwords.
        :type dto: UserPasswordChangeIn
        :raises NotFoundError: When user not found.
        :raises ServiceError: When old password verification fails.
        """

        with self.rw_uow() as uow:
            repo: UserRepository = uow.users
            user = repo.get_for_update(dto.user_id)
            if user is None:
                raise NotFoundError("User", dto.user_id)

            if not user.verify_password(dto.old_password):
                raise ServiceError("Old password is incorrect.")

            repo.update_password(dto.user_id, dto.new_password)
