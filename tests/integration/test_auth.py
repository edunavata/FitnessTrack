"""Integration tests for authentication endpoints."""

from __future__ import annotations


def test_register_and_login(client) -> None:
    """A user can register then obtain a JWT by logging in."""

    payload = {"email": "user@example.com", "password": "secret123"}

    # Register
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201

    # Login
    resp = client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_me_endpoint_requires_auth(client, auth_header, user) -> None:
    """Authenticated request to ``/me`` returns user info."""

    resp = client.get("/api/v1/auth/me", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == user.id
    assert data["email"] == user.email

