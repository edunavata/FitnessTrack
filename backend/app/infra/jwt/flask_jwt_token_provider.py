# app/infra/jwt/flask_jwt_token_provider.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from app.services._shared.ports import TokenProvider


@dataclass(slots=True)
class JWTTokenProvider(TokenProvider):
    """
    Adapter for Flask-JWT-Extended.

    .. note::
       Requires an active Flask app context with proper JWT settings.
    """

    def _merge_claims(self, base: dict[str, Any] | None, extra: dict[str, Any]) -> dict[str, Any]:
        """Merge claim dictionaries without mutating inputs."""
        merged = dict(base or {})
        merged.update(extra)
        return merged

    def create_access_token(
        self,
        *,
        identity: str | int,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
        fresh: bool = False,
        jti: str | None = None,
    ) -> str:
        # NOTE: Flask-JWT-Extended generates a jti by default.
        # We allow overriding it to keep the interface symmetric and for rare cases
        # like mapping ATs in a denylist. We'll pass it via additional_claims and assert.
        from flask_jwt_extended import create_access_token as _create_access
        from flask_jwt_extended import decode_token as _decode

        claims = additional_claims or {}
        if jti is not None:
            # Add/override 'jti' explicitly
            claims = self._merge_claims(claims, {"jti": jti})

        token = cast(
            str,
            _create_access(
                identity=identity,
                additional_claims=claims,
                expires_delta=expires_delta,
                fresh=fresh,
            ),
        )

        if jti is not None:
            # Safety assertion: ensure the library didn't overwrite our custom jti.
            # If it did, fail fast to avoid drift between token and server-side state.
            actual = cast(dict[str, Any], _decode(token))["jti"]
            if actual != jti:
                raise RuntimeError("Access token jti mismatch after creation.")

        return token

    def create_refresh_token(
        self,
        *,
        identity: str | int,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
        jti: str,
    ) -> str:
        # IMPORTANT:
        # - The refresh jti MUST come from the store (Redis/DB) that performs atomic rotation.
        # - We embed that jti into the JWT so the refresh endpoint can look it up.
        from flask_jwt_extended import create_refresh_token as _create_refresh
        from flask_jwt_extended import decode_token as _decode

        claims = self._merge_claims(additional_claims, {"jti": jti})

        token = cast(
            str,
            _create_refresh(
                identity=identity,
                additional_claims=claims,
                expires_delta=expires_delta,
            ),
        )

        # Safety assertion: ensure the token carries the provided jti (no silent override).
        actual = cast(dict[str, Any], _decode(token))["jti"]
        if actual != jti:
            raise RuntimeError("Refresh token jti mismatch after creation.")

        return token

    def decode(self, token: str) -> dict[str, Any]:
        from flask_jwt_extended import decode_token

        return cast(dict[str, Any], decode_token(token))

    def get_jti(self, token: str) -> str:
        return cast(str, self.decode(token)["jti"])

    def get_subject(self, token: str) -> int | str:
        subject = self.decode(token)["sub"]
        return cast(int | str, subject)

    def get_token_type(self, token: str) -> str:
        # Flask-JWT-Extended sets "type": "access" | "refresh"
        return cast(str, self.decode(token)["type"])

    def get_expires_at(self, token: str) -> datetime:
        exp = int(self.decode(token)["exp"])
        return datetime.fromtimestamp(exp, tz=UTC)
