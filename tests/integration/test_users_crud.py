"""Placeholder tests for future user CRUD endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="User CRUD endpoints not implemented yet")


def test_create_user() -> None:
    """Test creating a user.

    TODO
    ----
    - 201 on success
    - 422 on invalid payload
    - 409 on duplicate email
    """


def test_read_user() -> None:
    """Test retrieving a user.

    TODO
    ----
    - 200 when found
    - 404 when not found
    """


def test_update_user() -> None:
    """Test updating a user.

    TODO
    ----
    - 200/204 on success
    - 422 on invalid payload
    - 404 when missing
    """


def test_delete_user() -> None:
    """Test deleting a user.

    TODO
    ----
    - 204 on success
    - subsequent 404 for idempotency
    """


def test_list_users() -> None:
    """Test listing users with pagination and filters.

    TODO
    ----
    - pagination fields
    - sort and filter parameters
    """

