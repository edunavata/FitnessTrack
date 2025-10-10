# comments in English; reST docstrings
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import redis  # type: ignore[import-untyped]
from app.services._shared.ports import RefreshSessionView, RefreshTokenStore, RotationResult

# (Unused now) Lua script kept to minimize diff footprint.
LUA_ROTATE = r""" ... (unchanged, no longer used) ... """


@dataclass(slots=True)
class RedisRefreshTokenStore(RefreshTokenStore):
    """
    Redis-backed refresh token store with atomic rotation.

    :param r: A Redis client (already connected).
    """

    r: redis.Redis

    # -------------------- helpers --------------------

    @staticmethod
    def _k(jti: str) -> str:
        return f"rt:{jti}"

    @staticmethod
    def _ku(user_id: str) -> str:
        return f"rt:u:{user_id}"

    @staticmethod
    def _to_ts(dt: datetime) -> int:
        # Keep original semantics: naive -> label as UTC (no conversion)
        return int(dt.replace(tzinfo=UTC).timestamp())

    # -------------------- API ------------------------

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
        Insert the refresh session *before* issuing the JWT to the client.

        This ensures there is no timing window where the JWT exists without a server-side record.
        """
        key = self._k(jti)
        ttl = max(1, self._to_ts(expires_at) - self._to_ts(datetime.now(UTC)))

        pipe = self.r.pipeline(transaction=True)
        pipe.hset(
            key,
            mapping={
                "user_id": user_id,
                "tv": str(tv),
                "issued_at": str(self._to_ts(issued_at)),
                "expires_at": str(self._to_ts(expires_at)),
                "used": "0",
                "revoked": "0",
                "fingerprint": fingerprint,
            },
        )
        if idle_deadline:
            pipe.hset(key, "idle_deadline", str(self._to_ts(idle_deadline)))
        if ip_first:
            pipe.hset(key, "ip_first", ip_first)
        if ua_last:
            pipe.hset(key, "ua_last", ua_last)

        pipe.expire(key, ttl)
        pipe.sadd(self._ku(user_id), jti)
        pipe.execute()

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

        This version uses Redis WATCH/MULTI/EXEC (optimistic locking) to emulate the
        exact logic formerly implemented in the Lua script:
        - Check existence and state of ``old_jti``.
        - Reject if revoked/used/expired.
        - Enforce fingerprint binding.
        - Mark old as used and create new entry with TTL in one atomic step.
        - Update the user index with the new JTI.
        """
        now_ts = self._to_ts(now)
        new_exp_ts = self._to_ts(new_expires_at)
        ttl = max(1, new_exp_ts - now_ts)
        new_idle_ts = self._to_ts(new_idle_deadline) if new_idle_deadline else None

        k_old = self._k(old_jti)
        k_new = self._k(new_jti)

        # Need user_id for the index key; if absent, treat as NOT_FOUND (same behavior)
        uid_b = self.r.hget(k_old, "user_id")
        if not uid_b:
            return RotationResult.NOT_FOUND
        uid = uid_b.decode()
        k_user = self._ku(uid)

        # Retry loop for optimistic locking in case of concurrent modifications
        while True:
            try:
                with self.r.pipeline() as p:
                    # Watch the keys that participate in the invariant
                    p.watch(k_old, k_new, k_user)

                    # Read current state of old
                    h = self.r.hgetall(k_old)
                    if not h:
                        p.unwatch()
                        return RotationResult.NOT_FOUND

                    # Decode helper
                    def _b(s: bytes, default: str = "") -> str:
                        return s.decode() if s is not None else default

                    revoked = _b(h.get(b"revoked"), "0") == "1"
                    used = _b(h.get(b"used"), "0") == "1"
                    exp = int(_b(h.get(b"expires_at"), "0"))
                    fp = _b(h.get(b"fingerprint"))
                    tv = _b(h.get(b"tv"))  # copied as-is (string), same as Lua

                    # Apply the same validations as the Lua script (same order/semantics)
                    if exp <= now_ts:
                        p.unwatch()
                        return RotationResult.EXPIRED
                    if revoked:
                        p.unwatch()
                        return RotationResult.REVOKED
                    if used:
                        p.unwatch()
                        return RotationResult.REUSED
                    if fp != fingerprint:
                        p.unwatch()
                        return RotationResult.FINGERPRINT_MISMATCH

                    # Start the transactional block
                    p.multi()
                    # Mark old as used
                    p.hset(k_old, "used", "1")

                    # Create new entry with same fields as Lua (copying tv)
                    mapping = {
                        "user_id": uid,
                        "tv": tv,
                        "issued_at": str(now_ts),
                        "expires_at": str(new_exp_ts),
                        "used": "0",
                        "revoked": "0",
                        "fingerprint": fingerprint,
                    }
                    p.hset(k_new, mapping=mapping)
                    if new_idle_ts is not None:
                        p.hset(k_new, "idle_deadline", str(new_idle_ts))
                    p.expire(k_new, ttl)

                    # Update user index: store JTI (not the key), same efecto que Lua
                    p.sadd(k_user, new_jti)

                    # Commit
                    p.execute()

                # Post-commit: update optional ip/ua (non-critical, as in original)
                if ip_now or ua_now:
                    pipe2 = self.r.pipeline(transaction=True)
                    if ip_now:
                        pipe2.hset(k_new, "ip_last", ip_now)
                    if ua_now:
                        pipe2.hset(k_new, "ua_last", ua_now)
                    pipe2.execute()

                return RotationResult.OK

            except redis.WatchError:
                # Concurrent modification detected; retry loop
                continue

    def mark_revoked(self, jti: str) -> bool:
        key = self._k(jti)
        uid_b = self.r.hget(key, "user_id")
        if not uid_b:
            # No session -> nothing to revoke
            return False
        uid = uid_b.decode()

        with self.r.pipeline(transaction=True) as p:
            # set revoked=1 (returns 1 if changed, 0 if already '1')
            p.hset(key, "revoked", "1")
            # remove jti from the *correct* user set (bytes -> str decode)
            p.srem(self._ku(uid), jti)
            out = cast(list[int], p.execute())

        # Consider success if either we changed the hash OR we actually removed from the set
        hset_changed = bool(out[0])
        srem_removed = bool(out[1])
        return hset_changed or srem_removed

    def revoke_all_for_user(self, user_id: str) -> int:
        key_u = self._ku(user_id)
        jt_is = [
            member.decode() if isinstance(member, bytes | bytearray) else str(member)
            for member in self.r.smembers(key_u)
        ]
        if not jt_is:
            return 0
        pipe = self.r.pipeline(transaction=True)
        for j in jt_is:
            pipe.hset(self._k(j), "revoked", "1")
        pipe.delete(key_u)
        pipe.execute()
        return len(jt_is)

    def get(self, jti: str) -> RefreshSessionView | None:
        key = self._k(jti)
        h = self.r.hgetall(key)
        if not h:
            return None

        def _b(s: bytes, default: str = "") -> str:
            return s.decode() if s is not None else default

        return RefreshSessionView(
            jti=jti,
            user_id=_b(h.get(b"user_id")),
            tv=int(_b(h.get(b"tv"), "0")),
            used=_b(h.get(b"used"), "0") == "1",
            revoked=_b(h.get(b"revoked"), "0") == "1",
            expires_at=datetime.fromtimestamp(int(_b(h.get(b"expires_at"), "0")), tz=UTC),
            fingerprint=_b(h.get(b"fingerprint")),
        )

    def list_user_sessions(self, user_id: str) -> Iterable[RefreshSessionView]:
        key_u = self._ku(user_id)
        # Normalize bytes -> str and sort for determinism (como antes)
        members = sorted(
            j.decode() if isinstance(j, bytes | bytearray) else str(j)
            for j in self.r.smembers(key_u)
        )

        stale: list[str] = []
        for j in members:
            v = self.get(j)
            if v:
                yield v
            else:
                # Underlying hash missing (expired/deleted) -> mark for cleanup
                stale.append(j)

        if stale:
            # Remove all stale entries from the user's index in one call
            self.r.srem(key_u, *stale)

    def touch_idle(self, jti: str, new_idle_deadline: datetime) -> bool:
        key = self._k(jti)
        result = cast(int, self.r.hset(key, "idle_deadline", str(self._to_ts(new_idle_deadline))))
        return result == 1
