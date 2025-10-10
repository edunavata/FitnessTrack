from __future__ import annotations

from datetime import datetime
from typing import Protocol


class TokenDenylistStore(Protocol):
    """
    Abstraction for a denylist store for **access tokens**.

    Methods are expected to be idempotent.
    """

    def is_revoked(self, jti: str) -> bool: ...
    def revoke_jti(self, *, jti: str, expires_at: datetime) -> None: ...
    def revoke_all_for_user(self, user_id: str) -> int: ...


class InMemoryDenylistStore(TokenDenylistStore):
    """Simple in-memory denylist for **access** tokens by JTI."""

    def __init__(self) -> None:
        self._revoked: dict[str, datetime] = {}

    def is_revoked(self, jti: str) -> bool:
        # Expired entries are not cleaned for simplicity in unit tests.
        return jti in self._revoked

    def revoke_jti(self, *, jti: str, expires_at: datetime) -> None:
        self._revoked[jti] = expires_at

    def revoke_all_for_user(self, user_id: int | str) -> int:
        # Not tracked per-user in this stub.
        return 0
