from datetime import UTC, datetime
from typing import cast

import redis  # type: ignore[import-untyped]


class RedisTokenDenylistStore:
    """
    Minimal denylist for **access tokens** by jti.
    """

    def __init__(self, r: redis.Redis):
        self.r = r

    @staticmethod
    def _k(jti: str) -> str:
        return f"deny:at:{jti}"

    def is_revoked(self, jti: str) -> bool:
        return cast(int, self.r.exists(self._k(jti))) == 1

    def revoke_jti(self, *, jti: str, expires_at: datetime) -> None:
        now = datetime.now(UTC).timestamp()
        ttl = max(1, int(expires_at.timestamp() - now))
        # store a small marker with TTL; idempotent
        self.r.set(self._k(jti), "1", ex=ttl)

    def revoke_all_for_user(self, user_id: str) -> int:
        """
        Optional: if you also store an index per user (deny:at:u:{user_id}),
        you can implement bulk revoke. Otherwise, rely on token_version.
        """
        return 0
