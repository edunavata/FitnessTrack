# tests/unit/services/test_redis_refresh_store.py
"""
Unit tests for RedisRefreshTokenStore using fakeredis.

These tests exercise the main flows:
- register + get
- rotate (success and error cases)
- mark_revoked
- revoke_all_for_user
- list_user_sessions cleanup
- touch_idle

They use fakeredis.FakeRedis so they run entirely in-memory and integrate with pytest.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import fakeredis
import pytest
from app.infra.redis.redis_refresh_token_store import RedisRefreshTokenStore
from app.services._shared.ports import RotationResult


def _now() -> datetime:
    """Return a timezone-aware UTC "now"."""
    return datetime.now(UTC)


def _jti(i: int) -> str:
    """Helper to build predictable JTIs for tests."""
    return f"jti-{i}"


@pytest.fixture
def fake_redis():
    """Provide a fresh FakeRedis instance for each test."""
    # fakeredis.FakeRedis implements eval and lua support sufficiently for these tests.
    r = fakeredis.FakeRedis()
    # ensure a clean starting point
    r.flushall()
    return r


@pytest.fixture
def store(fake_redis):
    """Provide a RedisRefreshTokenStore backed by FakeRedis."""
    return RedisRefreshTokenStore(r=fake_redis)


def _make_expired(dt: datetime) -> datetime:
    """Return a datetime in the past relative to dt."""
    return dt - timedelta(seconds=10)


def _make_future(dt: datetime, seconds: int = 300) -> datetime:
    """Return a datetime in the future relative to dt."""
    return dt + timedelta(seconds=seconds)


def test_register_and_get(store):
    """
    Test that register inserts a session and get() retrieves it.

    - register a refresh session
    - get it back and validate fields
    """
    now = _now()
    jti = _jti(1)
    store.register(
        jti=jti,
        user_id="user-1",
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="fp-1",
        ip_first="1.2.3.4",
        ua_last="ua/1",
    )

    view = store.get(jti)
    assert view is not None
    assert view.jti == jti
    assert view.user_id == "user-1"
    assert view.fingerprint == "fp-1"
    assert view.used is False
    assert view.revoked is False
    assert view.expires_at > now


def test_rotate_success(store):
    """
    Successful rotation:

    - register old_jti
    - call rotate(old->new) with correct fingerprint
    - assert RotationResult.OK and new session exists and old marked used
    """
    now = _now()
    old = _jti(2)
    new = _jti(3)
    user = "u2"
    store.register(
        jti=old,
        user_id=user,
        tv=7,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="device-x",
    )

    res = store.rotate(
        old_jti=old,
        new_jti=new,
        now=now,
        new_expires_at=_make_future(now, 300),
        fingerprint="device-x",
        ip_now="9.9.9.9",
        ua_now="ua/2",
    )
    assert res == RotationResult.OK

    old_view = store.get(old)
    new_view = store.get(new)
    assert old_view is not None and old_view.used is True
    assert new_view is not None and new_view.used is False
    assert new_view.user_id == user


def test_rotate_not_found(store):
    """Rotation of non-existing old_jti must return NOT_FOUND."""
    now = _now()
    res = store.rotate(
        old_jti="no-such",
        new_jti="new-no",
        now=now,
        new_expires_at=_make_future(now, 300),
        fingerprint="any",
    )
    assert res == RotationResult.NOT_FOUND


def test_rotate_fingerprint_mismatch(store):
    """Rotation fails when fingerprint doesn't match."""
    now = _now()
    old = _jti(4)
    new = _jti(5)
    store.register(
        jti=old,
        user_id="u4",
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="good-fp",
    )

    res = store.rotate(
        old_jti=old,
        new_jti=new,
        now=now,
        new_expires_at=_make_future(now, 300),
        fingerprint="bad-fp",
    )
    assert res == RotationResult.FINGERPRINT_MISMATCH


def test_rotate_expired(store):
    """Rotation fails if the old token is expired."""
    now = _now()
    old = _jti(6)
    new = _jti(7)
    # register with an expiry in the past
    store.register(
        jti=old,
        user_id="u6",
        tv=1,
        expires_at=_make_expired(now),
        issued_at=now - timedelta(seconds=60),
        fingerprint="fp",
    )

    res = store.rotate(
        old_jti=old,
        new_jti=new,
        now=now,
        new_expires_at=_make_future(now, 300),
        fingerprint="fp",
    )
    assert res == RotationResult.EXPIRED


def test_rotate_reused_and_revoked(store):
    """Rotation fails when old_jti is marked used or revoked."""
    now = _now()
    # Reused case
    old_reused = _jti(8)
    new_reused = _jti(9)
    store.register(
        jti=old_reused,
        user_id="u8",
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="fp",
    )
    # mark as used manually
    store.r.hset(store._k(old_reused), "used", "1")

    res_reused = store.rotate(
        old_jti=old_reused,
        new_jti=new_reused,
        now=now,
        new_expires_at=_make_future(now, 300),
        fingerprint="fp",
    )
    assert res_reused == RotationResult.REUSED

    # Revoked case
    old_revoked = _jti(10)
    new_revoked = _jti(11)
    store.register(
        jti=old_revoked,
        user_id="u10",
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="fp",
    )
    store.r.hset(store._k(old_revoked), "revoked", "1")

    res_revoked = store.rotate(
        old_jti=old_revoked,
        new_jti=new_revoked,
        now=now,
        new_expires_at=_make_future(now, 300),
        fingerprint="fp",
    )
    assert res_revoked == RotationResult.REVOKED


def test_mark_revoked_and_revoke_all(store):
    """
    Test mark_revoked removes the jti from the user index (best-effort)
    and returns a boolean. Test revoke_all_for_user marks all and clears the set.
    """
    now = _now()
    jtis = [_jti(20), _jti(21), _jti(22)]
    user = "bulk-1"
    for j in jtis:
        store.register(
            jti=j,
            user_id=user,
            tv=2,
            expires_at=_make_future(now, 120),
            issued_at=now,
            fingerprint="fp",
        )

    # mark a single one revoked
    ok = store.mark_revoked(jtis[0])
    assert ok is True
    # the jti should no longer be a member of the user's set (best-effort)
    members = [
        member.decode() if isinstance(member, bytes | bytearray) else str(member)
        for member in store.r.smembers(store._ku(user))
    ]
    assert jtis[0] not in members

    # revoke all remaining
    count = store.revoke_all_for_user(user)
    # number of items returned should equal remaining jtis (2)
    assert count == 2
    assert store.r.scard(store._ku(user)) == 0
    # check that keys are marked revoked
    for j in jtis[1:]:
        assert store.r.hget(store._k(j), "revoked") == b"1"


def test_list_user_sessions_cleans_stale(store):
    """
    list_user_sessions must yield existing sessions and remove stale (non-existent) JTIs
    from the user's set.
    """
    now = _now()
    user = "cleaner"
    existing = _jti(30)
    stale = _jti(31)

    store.register(
        jti=existing,
        user_id=user,
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="fp",
    )
    store.register(
        jti=stale,
        user_id=user,
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="fp",
    )

    # simulate expiry by deleting the underlying key for 'stale'
    store.r.delete(store._k(stale))

    sessions = list(store.list_user_sessions(user))
    # should yield only the existing one
    assert any(s.jti == existing for s in sessions)
    assert all(s.jti != stale for s in sessions)
    # stale should have been removed from the set
    members = [
        member.decode() if isinstance(member, bytes | bytearray) else str(member)
        for member in store.r.smembers(store._ku(user))
    ]
    assert stale not in members


def test_touch_idle(store):
    """touch_idle updates the idle_deadline field and returns a truthy value."""
    now = _now()
    j = _jti(40)
    store.register(
        jti=j,
        user_id="u40",
        tv=1,
        expires_at=_make_future(now, 120),
        issued_at=now,
        fingerprint="fp",
    )

    new_deadline = _make_future(now, 50)
    ok = store.touch_idle(j, new_deadline)
    # FakeRedis returns 1 when a field is set; the implementation returns that result==1
    assert ok is True or ok == 1
    # verify value stored
    stored = store.r.hget(store._k(j), "idle_deadline")
    assert stored is not None
