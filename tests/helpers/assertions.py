"""Assertion helper utilities for tests."""

from __future__ import annotations


def assert_json_keys(data: dict, required: set[str]) -> None:
    """Ensure that all required keys are present in ``data``.

    Parameters
    ----------
    data:
        JSON object under test.
    required:
        Set of required keys that must exist in ``data``.

    Raises
    ------
    AssertionError
        If any required key is missing.
    """

    missing = required - data.keys()
    assert not missing, f"Missing keys: {', '.join(sorted(missing))}"


def assert_pagination(obj: dict) -> None:
    """Validate a standard pagination response structure.

    Parameters
    ----------
    obj:
        JSON object representing a paginated response.
    """

    assert_json_keys(obj, {"items", "total", "page", "limit"})
    assert isinstance(obj["items"], list)

