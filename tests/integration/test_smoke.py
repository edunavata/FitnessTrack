"""Basic smoke tests for the API."""

from __future__ import annotations


def test_healthz(client) -> None:
    """Health endpoint returns a simple status payload."""

    # Act
    resp = client.get("/api/v1/healthz")

    # Assert
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_readiness(client) -> None:
    """Readiness endpoint indicates readiness."""

    resp = client.get("/api/v1/readiness")
    assert resp.status_code == 200
    assert resp.get_json() == {"ready": True}


def test_cors_headers(client) -> None:
    """CORS headers should reflect allowed origins."""

    resp = client.get("/api/v1/healthz", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"

