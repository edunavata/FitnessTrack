from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Protocol
from uuid import uuid4


class RotationResult(Enum):
    """Outcome of an atomic refresh rotation attempt."""

    OK = auto()
    NOT_FOUND = auto()
    EXPIRED = auto()
    REVOKED = auto()
    REUSED = auto()
    FINGERPRINT_MISMATCH = auto()


@dataclass(frozen=True)
class RefreshSessionView:
    """
    Read-model for a refresh session.

    :ivar jti: Refresh token identifier.
    :ivar user_id: Owner user id.
    :ivar tv: Token version snapshot at issuance.
    :ivar used: Whether the RT has been consumed for rotation.
    :ivar revoked: Whether the RT has been explicitly revoked.
    :ivar expires_at: Absolute expiration (UTC).
    :ivar fingerprint: Binding marker (device or client context).
    """

    jti: str
    user_id: str
    tv: int
    used: bool
    revoked: bool
    expires_at: datetime
    fingerprint: str


class RefreshTokenStore(Protocol):
    """
    Stateful store for refresh sessions.

    All write operations MUST be idempotent or atomic, and the rotation MUST be atomic.
    """

    def register(
        self,
        *,
        jti: str,
        user_id: str,
        tv: int,
        expires_at: datetime,
        issued_at: datetime,
        fingerprint: str,
        ip_first: str | None = None,
        ua_last: str | None = None,
        idle_deadline: datetime | None = None,
    ) -> None:
        """
        Create a brand-new refresh session entry.

        This MUST be executed *before* the JWT is handed to the client.
        """

    def rotate(
        self,
        *,
        old_jti: str,
        new_jti: str,
        now: datetime,
        new_expires_at: datetime,
        fingerprint: str,
        ip_now: str | None = None,
        ua_now: str | None = None,
        new_idle_deadline: datetime | None = None,
    ) -> RotationResult:
        """
        Atomically consume ``old_jti`` and create ``new_jti``.

        :returns: ``RotationResult.OK`` on success, otherwise the specific failure.
        """

    def mark_revoked(self, jti: str) -> bool:
        """Mark a single session as revoked. :returns: True if it existed."""

    def revoke_all_for_user(self, user_id: str) -> int:
        """
        Revoke all sessions for the given user.

        :returns: Number of sessions affected.
        """

    def get(self, jti: str) -> RefreshSessionView | None:
        """Fetch a single session snapshot (if present)."""

    def list_user_sessions(self, user_id: str) -> Iterable[RefreshSessionView]:
        """List active (non-expired) sessions for a user."""

    def touch_idle(self, jti: str, new_idle_deadline: datetime) -> bool:
        """Update idle deadline (if you enforce idle timeouts)."""

    def new_jti(self) -> str:
        """Generate a new random refresh token identifier."""
        return uuid4().hex


@dataclass(frozen=True)
class _Session:
    user_id: str
    tv: int
    issued_at: int
    expires_at: int
    used: bool
    revoked: bool
    fingerprint: str


class InMemoryRefreshTokenStore(RefreshTokenStore):
    """
    In-memory refresh session store with atomic rotation behavior.

    .. note::
       Uses a threading lock to simulate atomicity in unit tests.
    """

    def __init__(self) -> None:
        self._by_jti: dict[str, _Session] = {}
        self._by_user: dict[str, set[str]] = {}
        self._seq = 0
        self._lock = threading.Lock()

    # ------------------------- helpers -------------------------

    def _ts(self, dt: datetime) -> int:
        return int(dt.replace(tzinfo=UTC).timestamp())

    def _now(self) -> int:
        return self._ts(datetime.now(UTC))

    # -------------------------- API ----------------------------

    def new_jti(self) -> str:
        """Generate a new JTI controlled by the store."""
        with self._lock:
            self._seq += 1
            return f"rt-{self._seq}"

    def register(
        self,
        *,
        jti: str,
        user_id: str,
        tv: int,
        expires_at: datetime,
        issued_at: datetime,
        fingerprint: str,
        ip_first: str | None = None,
        ua_last: str | None = None,
        idle_deadline: datetime | None = None,
    ) -> None:
        with self._lock:
            self._by_jti[jti] = _Session(
                user_id=user_id,
                tv=tv,
                issued_at=self._ts(issued_at),
                expires_at=self._ts(expires_at),
                used=False,
                revoked=False,
                fingerprint=fingerprint,
            )
            self._by_user.setdefault(user_id, set()).add(jti)

    def rotate(
        self,
        *,
        old_jti: str,
        new_jti: str,
        now: datetime,
        new_expires_at: datetime,
        fingerprint: str,
        ip_now: str | None = None,
        ua_now: str | None = None,
        new_idle_deadline: datetime | None = None,
    ) -> RotationResult:
        with self._lock:
            s = self._by_jti.get(old_jti)
            if not s:
                return RotationResult.NOT_FOUND
            if s.expires_at <= self._now():
                return RotationResult.EXPIRED
            if s.revoked:
                return RotationResult.REVOKED
            if s.used:
                return RotationResult.REUSED
            if s.fingerprint != fingerprint:
                return RotationResult.FINGERPRINT_MISMATCH

            # mark old as used and create new session
            self._by_jti[old_jti] = _Session(
                user_id=s.user_id,
                tv=s.tv,
                issued_at=s.issued_at,
                expires_at=s.expires_at,
                used=True,
                revoked=False,
                fingerprint=s.fingerprint,
            )
            self._by_jti[new_jti] = _Session(
                user_id=s.user_id,
                tv=s.tv,
                issued_at=self._now(),
                expires_at=self._ts(new_expires_at),
                used=False,
                revoked=False,
                fingerprint=fingerprint,
            )
            self._by_user.setdefault(s.user_id, set()).add(new_jti)
            return RotationResult.OK

    def mark_revoked(self, jti: str) -> bool:
        with self._lock:
            s = self._by_jti.get(jti)
            if not s:
                return False
            self._by_jti[jti] = _Session(
                user_id=s.user_id,
                tv=s.tv,
                issued_at=s.issued_at,
                expires_at=s.expires_at,
                used=s.used,
                revoked=True,
                fingerprint=s.fingerprint,
            )
            # keep index for visibility; real store might also remove
            return True

    def revoke_all_for_user(self, user_id: str) -> int:
        with self._lock:
            jt_is = list(self._by_user.get(user_id, set()))
            for j in jt_is:
                if j in self._by_jti:
                    s = self._by_jti[j]
                    self._by_jti[j] = _Session(
                        user_id=s.user_id,
                        tv=s.tv,
                        issued_at=s.issued_at,
                        expires_at=s.expires_at,
                        used=s.used,
                        revoked=True,
                        fingerprint=s.fingerprint,
                    )
            return len(jt_is)

    def get(self, jti: str) -> RefreshSessionView | None:
        s = self._by_jti.get(jti)
        if not s:
            return None
        return RefreshSessionView(
            jti=jti,
            user_id=s.user_id,
            tv=s.tv,
            used=s.used,
            revoked=s.revoked,
            expires_at=datetime.fromtimestamp(s.expires_at, tz=UTC),
            fingerprint=s.fingerprint,
        )

    def list_user_sessions(self, user_id: str):
        for j in sorted(self._by_user.get(user_id, set())):
            v = self.get(j)
            if v:
                yield v

    def touch_idle(self, jti: str, new_idle_deadline: datetime) -> bool:
        # no-op for tests
        return True
