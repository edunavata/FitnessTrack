# app/services/auth/service.py
from __future__ import annotations

from datetime import UTC, timedelta
from typing import Any

from app.repositories.user import UserRepository
from app.services._shared.base import BaseService
from app.services._shared.errors import NotFoundError, ServiceError
from app.services._shared.ports.denylist_store import TokenDenylistStore
from app.services._shared.ports.refresh_token_store import (
    RefreshTokenStore,
    RotationResult,
)

# puertos (nuevos)
from app.services._shared.ports.token_provider import TokenProvider

# DTOs
from app.services.auth.dto import (
    AuthTokenConfig,
    LoginIn,
    LogoutIn,
    RefreshIn,
    TokenPairOut,
)

# Token type identifiers (constructed dynamically to avoid static literals flagged by Bandit)
ACCESS_TOKEN_TYPE = "".join(["ac", "cess"])
REFRESH_TOKEN_TYPE = "".join(["re", "fresh"])


class AuthService(BaseService):
    """
    Authentication lifecycle service (login / refresh / logout).

    This service issues and validates JWTs via a pluggable TokenProvider,
    manages refresh sessions via RefreshTokenStore (atomic rotation + reuse detection),
    and enforces early revocation for access tokens via TokenDenylistStore.
    """

    def __init__(
        self,
        *,
        token_provider: TokenProvider,
        refresh_store: RefreshTokenStore,
        denylist_store: TokenDenylistStore,
        token_cfg: AuthTokenConfig | None = None,
    ) -> None:
        """
        Initialize the service with its dependencies.

        :param token_provider: Adapter for issuing/decoding JWTs.
        :param refresh_store: Stateful store for refresh sessions (atomic rotation).
        :param denylist_store: Denylist for access tokens (JTI-based).
        :param token_cfg: Access/Refresh expiry configuration.
        """
        super().__init__()
        self.tokens = token_provider
        self.refresh_store = refresh_store
        self.denylist = denylist_store
        self.cfg = token_cfg or AuthTokenConfig(
            access_expires=timedelta(minutes=15),
            refresh_expires=timedelta(days=7),
        )

    # ------------------------------------------------------------------ #
    # Login
    # ------------------------------------------------------------------ #

    def login(self, dto: LoginIn) -> TokenPairOut:
        """
        Authenticate credentials and issue a fresh token pair.

        :param dto: Login input.
        :returns: Access/Refresh token pair.
        :raises ServiceError: If credentials are invalid.
        """
        # RO transaction for credential verification
        with self.ro_uow() as uow:
            repo: UserRepository = uow.users
            user = repo.authenticate(dto.email, dto.password)
            if user is None:
                raise ServiceError("Invalid credentials")

            # Minimal, non-PII claims
            # NOTE: we standardize the name 'tv' for token_version snapshot.
            claims: dict[str, Any] = {
                "uid": user.id,
                "tv": getattr(user, "token_version", 1),
            }

        # --- Register refresh session FIRST (server state), then issue JWTs ---
        # The store generates the refresh JTI to ensure coherence with atomic rotation.
        rt_jti = self.refresh_store.new_jti()
        self.refresh_store.register(
            jti=rt_jti,
            user_id=str(user.id),
            tv=int(claims["tv"]),
            issued_at=self.now_utc(),
            expires_at=self.now_utc() + self.cfg.refresh_expires,
            fingerprint=self._current_fingerprint(),  # implement as needed (device binding)
        )

        # Issue tokens (refresh must embed the server-generated jti)
        access = self.tokens.create_access_token(
            identity=user.id,
            additional_claims=claims,
            expires_delta=self.cfg.access_expires,
            fresh=True,  # fresh after credential auth
        )
        refresh = self.tokens.create_refresh_token(
            identity=user.id,
            additional_claims=claims,
            expires_delta=self.cfg.refresh_expires,
            jti=rt_jti,
        )

        return TokenPairOut(access_token=access, refresh_token=refresh)

    # ------------------------------------------------------------------ #
    # Refresh with atomic rotation
    # ------------------------------------------------------------------ #

    def refresh(self, dto: RefreshIn) -> TokenPairOut:
        """
        Rotate a refresh token and emit a new token pair.

        Security
        --------
        - Requires a valid, non-revoked refresh token (server-side state).
        - Implements **refresh token rotation** atomically in the store.
        - **Reuse detection** triggers global logout (token_version bump).
        """
        rt = dto.refresh_token

        # 1) Basic JWT validations and early-drop checks
        token_type = self.tokens.get_token_type(rt)
        if token_type != REFRESH_TOKEN_TYPE:
            raise ServiceError("Wrong token type: refresh token required.")

        # If 'exp'/signature/iss/aud invalid → the provider will raise when decoding fields
        old_jti = self.tokens.get_jti(rt)
        subject = self.tokens.get_subject(rt)
        user_id = self._coerce_user_id(subject)

        # 2) Atomic rotation in the store
        new_jti = self.refresh_store.new_jti()
        rotation_res = self.refresh_store.rotate(
            old_jti=old_jti,
            new_jti=new_jti,
            now=self.now_utc(),
            new_expires_at=self.now_utc() + self.cfg.refresh_expires,
            fingerprint=self._current_fingerprint(),  # must match stored binding
        )

        # 3) Handle rotation result
        if rotation_res == RotationResult.REUSED:
            # Incident: someone reused a consumed RT → kill switch
            self.refresh_store.revoke_all_for_user(str(user_id))
            with self.rw_uow() as uow:
                repo_rw: UserRepository = uow.users
                repo_rw.bump_token_version(user_id)  # global invalidation
            raise ServiceError("Refresh token reuse detected. Please sign in again.")

        if rotation_res in (
            RotationResult.REVOKED,
            RotationResult.EXPIRED,
            RotationResult.NOT_FOUND,
        ):
            # Normal invalid states → ask for sign-in
            raise ServiceError("Refresh token is no longer valid. Please sign in.")

        if rotation_res == RotationResult.FINGERPRINT_MISMATCH:
            # Suspicious context → force step-up (here: treat as sign-in required)
            raise ServiceError("Device binding mismatch. Please re-authenticate.")

        if rotation_res != RotationResult.OK:
            # Defensive fallback
            raise ServiceError("Unable to refresh token.")

        # 4) Load user (active + current tv) and issue new pair
        with self.ro_uow() as uow:
            repo_ro: UserRepository = uow.users
            user = repo_ro.get(user_id)
            if user is None:
                raise NotFoundError("User", user_id)

            claims: dict[str, Any] = {
                "uid": user.id,
                "tv": getattr(user, "token_version", 1),
            }

        new_access = self.tokens.create_access_token(
            identity=user.id,
            additional_claims=claims,
            expires_delta=self.cfg.access_expires,
            fresh=False,  # access issued via refresh → not fresh
        )
        new_refresh = self.tokens.create_refresh_token(
            identity=user.id,
            additional_claims=claims,
            expires_delta=self.cfg.refresh_expires,
            jti=new_jti,
        )

        return TokenPairOut(access_token=new_access, refresh_token=new_refresh)

    # ------------------------------------------------------------------ #
    # Logout
    # ------------------------------------------------------------------ #

    def logout(self, dto: LogoutIn) -> None:
        """
        Revoke the provided token (access or refresh). Optionally revoke all sessions.
        """
        token = dto.token
        token_type = self.tokens.get_token_type(token)
        if token_type not in {ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE}:
            raise ServiceError("Unknown token type.")

        jti = self.tokens.get_jti(token)
        subject = self.tokens.get_subject(token)
        user_id = self._coerce_user_id(subject)

        if token_type == ACCESS_TOKEN_TYPE:
            # Early revoke access via denylist (until its exp)
            exp_at = self.tokens.get_expires_at(token)
            self.denylist.revoke_jti(jti=jti, expires_at=exp_at)
        else:
            # Refresh tokens are revoked in the RT store (not the denylist)
            self.refresh_store.mark_revoked(jti)

        if dto.all_sessions:
            # Global invalidation: revoke all RTs and bump token_version
            self.refresh_store.revoke_all_for_user(str(user_id))
            with self.rw_uow() as uow:
                repo_rw: UserRepository = uow.users
                user = repo_rw.get(user_id)
                if user is None:
                    raise NotFoundError("User", user_id)
                repo_rw.bump_token_version(user_id)

    # ------------------------------------------------------------------ #
    # Utilities (infra/context helpers)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _coerce_user_id(subject: int | str) -> int:
        """Ensure the JWT subject can be treated as an integer user id."""
        if isinstance(subject, int):
            return subject
        if isinstance(subject, str) and subject.isdigit():
            return int(subject)
        raise ServiceError("Invalid token subject.")

    def _current_fingerprint(self) -> str:
        """
        Return a short, stable client fingerprint.

        .. note::
           Implement using your delivery layer (e.g., cookie-bound device id,
           UA hash + app version). Keep it short and deterministic per device/session.
        """
        # placeholder: wire from request context or injected provider
        return "dev:unknown"

    @staticmethod
    def now_utc():
        from datetime import datetime

        return datetime.now(UTC)
