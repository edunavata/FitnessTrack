"""HTTP helper utilities for tests."""

from __future__ import annotations

from urllib.parse import urlencode


def json_headers(auth_token: str | None = None) -> dict[str, str]:
    """Return standard JSON headers.

    Parameters
    ----------
    auth_token:
        Optional bearer token to include.

    Returns
    -------
    dict[str, str]
        HTTP headers dictionary.
    """

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def build_url(path: str, **query: str | int | float) -> str:
    """Build a URL with encoded query parameters.

    Parameters
    ----------
    path:
        Base path of the endpoint.
    **query:
        Query parameters to append.

    Returns
    -------
    str
        Final URL string including encoded query string.
    """

    qs = urlencode({k: v for k, v in query.items() if v is not None})
    return f"{path}?{qs}" if qs else path

