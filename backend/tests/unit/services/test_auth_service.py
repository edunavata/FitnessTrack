# tests/unit/services/test_auth_service.py
from __future__ import annotations

import pytest
from app.services._shared.errors import NotFoundError, ServiceError
from app.services._shared.ports.denylist_store import InMemoryDenylistStore
from app.services._shared.ports.refresh_token_store import InMemoryRefreshTokenStore
from app.services._shared.ports.token_provider import StubTokenProvider
from app.services.auth.dto import LoginIn, LogoutIn, RefreshIn, TokenPairOut
from app.services.auth.service import AuthService
from tests.factories.subject import SubjectFactory  # <-- IMPORTANTE
from tests.factories.user import UserFactory


# ------------------------------ Fixtures ---------------------------------- #
@pytest.fixture()
def service() -> AuthService:
    """
    Build an AuthService wired to in-memory doubles.

    .. note::
       Uses a fixed fingerprint "dev:unknown" to match AuthService default.
    """
    return AuthService(
        token_provider=StubTokenProvider(),
        refresh_store=InMemoryRefreshTokenStore(),
        denylist_store=InMemoryDenylistStore(),
    )


# -------------------------------- Tests ----------------------------------- #
def test_login_issues_token_pair_and_registers_rt(service, session):
    """Login returns a token pair and registers the refresh session in the store."""
    user = UserFactory(email="a@a.com", password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()

    pair = service.login(LoginIn(email=user.email, password="x"))
    assert isinstance(pair, TokenPairOut)
    assert pair.access_token.startswith("access.")
    assert pair.refresh_token.startswith("refresh.")

    # Ensure RT was registered with 'used=False'
    rt_jti = service.tokens.get_jti(pair.refresh_token)
    view = service.refresh_store.get(rt_jti)
    assert view is not None
    assert view.used is False
    assert view.revoked is False
    assert view.user_id == str(user.id)


def test_login_invalid_credentials(service):
    with pytest.raises(ServiceError):
        service.login(LoginIn(email="missing@example.com", password="x"))


def test_refresh_rotates_and_blocks_reuse(service, session):
    """First refresh rotates; reusing the old RT is treated as incident (ServiceError)."""
    user = UserFactory(password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()

    pair1 = service.login(LoginIn(email=user.email, password="x"))

    # First refresh rotates successfully
    pair2 = service.refresh(RefreshIn(refresh_token=pair1.refresh_token))
    assert pair2.refresh_token != pair1.refresh_token  # rotated

    # Old RT cannot be used again (reuse -> ServiceError)
    with pytest.raises(ServiceError):
        service.refresh(RefreshIn(refresh_token=pair1.refresh_token))

    # Store reflects states
    old_jti = service.tokens.get_jti(pair1.refresh_token)
    new_jti = service.tokens.get_jti(pair2.refresh_token)
    old_view = service.refresh_store.get(old_jti)
    new_view = service.refresh_store.get(new_jti)
    assert old_view and old_view.used is True
    assert new_view and new_view.used is False


def test_refresh_fails_if_user_deleted(service, session):
    """Refresh fails with NotFound if the user no longer exists."""
    user = UserFactory(password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()
    pair = service.login(LoginIn(email=user.email, password="x"))

    # Simulate user deletion
    session.delete(user)
    session.flush()

    with pytest.raises(NotFoundError):
        service.refresh(RefreshIn(refresh_token=pair.refresh_token))


def test_logout_access_revokes_in_denylist(service, session):
    """Logout with access token adds its JTI to the denylist."""
    user = UserFactory(password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()
    pair = service.login(LoginIn(email=user.email, password="x"))

    jti_access = service.tokens.get_jti(pair.access_token)
    assert service.denylist.is_revoked(jti_access) is False

    service.logout(LogoutIn(token=pair.access_token, all_sessions=False))
    assert service.denylist.is_revoked(jti_access) is True


def test_logout_refresh_revokes_in_store_and_all_sessions(service, session):
    """Logout with refresh marks it revoked; all_sessions revokes every RT for the user."""
    user = UserFactory(password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()
    pair = service.login(LoginIn(email=user.email, password="x"))

    # Revoke just the refresh used in the request
    rt_jti = service.tokens.get_jti(pair.refresh_token)
    service.logout(LogoutIn(token=pair.refresh_token, all_sessions=False))
    v = service.refresh_store.get(rt_jti)
    assert v and v.revoked is True

    # Issue another session and then revoke all
    pair2 = service.login(LoginIn(email=user.email, password="x"))
    service.logout(LogoutIn(token=pair2.refresh_token, all_sessions=True))

    # All sessions for the user should be revoked now
    for sess in service.refresh_store.list_user_sessions(str(user.id)):
        assert sess.revoked is True


def test_refresh_fingerprint_mismatch_requires_reauth(service, session, monkeypatch):
    """
    If the fingerprint does not match the one stored with the RT, refresh is rejected.
    """
    user = UserFactory(password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()

    pair = service.login(LoginIn(email=user.email, password="x"))

    # Force a different fingerprint for this call
    monkeypatch.setattr(service, "_current_fingerprint", lambda: "dev:other-device")

    with pytest.raises(ServiceError):
        service.refresh(RefreshIn(refresh_token=pair.refresh_token))


def test_reuse_triggers_token_version_bump(service, session):
    """
    Reusing an already-consumed RT should trigger a token_version bump (global logout).
    We check it by reloading the user after the reuse incident.
    """
    user = UserFactory(password="x")
    SubjectFactory(user=user)  # <-- crear Subject enlazado
    session.flush()
    pair1 = service.login(LoginIn(email=user.email, password="x"))

    # First refresh is OK
    pair2 = service.refresh(RefreshIn(refresh_token=pair1.refresh_token))
    assert pair2.refresh_token != pair1.refresh_token

    # Reuse old token -> ServiceError and bump
    with pytest.raises(ServiceError):
        service.refresh(RefreshIn(refresh_token=pair1.refresh_token))

    # Reload user and ensure token_version increased
    session.refresh(user)
    # user model is likely cached; refetch from DB via a new query if needed
    # We expect bump_token_version to have incremented it by +1
    assert getattr(user, "token_version", 1) >= 2
