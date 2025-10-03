"""Smoke tests for the API blueprint wiring."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(BACKEND_ROOT.resolve()))

from app import create_app
from app.core.extensions import db


@pytest.fixture
def app():
    """Create a Flask application configured for testing."""

    os.environ.setdefault("APP_ENV", "testing")
    application = create_app()
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Return a test client bound to the application."""

    return app.test_client()


def test_health_endpoint(client):
    """Health check should return OK payload."""

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] in {"ok", "degraded"}


def test_exercises_list_envelope(client):
    """List endpoint returns pagination envelope even when empty."""

    response = client.get("/api/v1/exercises?limit=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload.keys()) == {"items", "page", "limit", "total"}
    assert isinstance(payload["items"], list)
