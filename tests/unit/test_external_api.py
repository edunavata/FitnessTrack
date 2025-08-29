"""Example unit test demonstrating external HTTP mocking."""

from __future__ import annotations

import requests
import responses


def fetch_status() -> dict:
    """Fetch JSON status from an external service."""

    resp = requests.get("https://example.com/status", timeout=1)
    resp.raise_for_status()
    return resp.json()


@responses.activate
def test_fetch_status_success() -> None:
    """Example of mocking a successful HTTP call with ``responses``."""

    # Arrange
    responses.add(
        responses.GET,
        "https://example.com/status",
        json={"ok": True},
        status=200,
    )

    # Act
    data = fetch_status()

    # Assert
    assert data == {"ok": True}

