from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol


class TokenProvider(Protocol):
    """Port for issuing and decoding JWT tokens."""

    def create_access_token(
        self,
        *,
        identity: int | str,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
        fresh: bool = False,
        jti: str | None = None,
    ) -> str: ...

    def create_refresh_token(
        self,
        *,
        identity: int | str,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
        jti: str,
    ) -> str: ...

    def decode(self, token: str) -> dict[str, Any]: ...

    def get_jti(self, token: str) -> str: ...

    def get_subject(self, token: str) -> int | str: ...

    def get_token_type(self, token: str) -> str: ...

    def get_expires_at(self, token: str) -> datetime: ...


class StubTokenProvider(TokenProvider):
    """Deterministic token provider used in unit tests."""

    def __init__(self) -> None:
        self._now = datetime.now(tz=UTC)
        self._seq = 0
        self._issued: dict[str, dict[str, Any]] = {}

    def _mk(
        self,
        *,
        identity: int | str,
        ttype: str,
        exp_delta: timedelta,
        jti: str | None = None,
        additional_claims: dict[str, Any] | None = None,
        fresh: bool | None = None,
    ) -> str:
        self._seq += 1
        jti_value = jti or f"jti-{self._seq}"
        token = f"{ttype}.{identity}.{jti_value}.{self._seq}"
        payload: dict[str, Any] = {
            "sub": identity,
            "type": ttype,
            "jti": jti_value,
            "exp": int((self._now + exp_delta).timestamp()),
        }
        if additional_claims:
            payload.update(additional_claims)
        if fresh is not None:
            payload["fresh"] = bool(fresh)
        self._issued[token] = payload
        return token

    def create_access_token(
        self,
        *,
        identity: int | str,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
        fresh: bool = False,
        jti: str | None = None,
    ) -> str:
        return self._mk(
            identity=identity,
            ttype="access",
            exp_delta=expires_delta or timedelta(minutes=15),
            jti=jti,
            additional_claims=additional_claims,
            fresh=fresh,
        )

    def create_refresh_token(
        self,
        *,
        identity: int | str,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
        jti: str,
    ) -> str:
        return self._mk(
            identity=identity,
            ttype="refresh",
            exp_delta=expires_delta or timedelta(days=7),
            jti=jti,
            additional_claims=additional_claims,
        )

    def decode(self, token: str) -> dict[str, Any]:
        return self._issued[token]

    def get_jti(self, token: str) -> str:
        return str(self.decode(token)["jti"])

    def get_subject(self, token: str) -> int | str:
        subject = self.decode(token)["sub"]
        if isinstance(subject, int | str):
            return subject
        raise TypeError(f"Unexpected subject type: {type(subject)!r}")

    def get_token_type(self, token: str) -> str:
        return str(self.decode(token)["type"])

    def get_expires_at(self, token: str) -> datetime:
        exp = int(self.decode(token)["exp"])
        return datetime.fromtimestamp(exp, tz=UTC)
