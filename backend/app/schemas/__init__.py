"""Helper functions and exports for Marshmallow schemas."""

from __future__ import annotations

from typing import Any, cast

from marshmallow import Schema, ValidationError

from app.core.errors import APIError


def load_data(schema: Schema, data: dict[str, Any]) -> dict[str, Any]:
    """Validate ``data`` against a Marshmallow ``schema``.

    Parameters
    ----------
    schema: Schema
        Marshmallow schema used to deserialize and validate the payload.
    data: dict[str, Any]
        Raw payload typically sourced from a Flask request body.

    Returns
    -------
    dict[str, Any]
        Deserialized Python data produced by ``schema.load``.

    Raises
    ------
    APIError
        Raised when validation fails; field errors are exposed under
        ``details``.
    """
    try:
        return cast(dict[str, Any], schema.load(data))
    except ValidationError as err:  # pragma: no cover - simple pass-through
        raise APIError(
            "Invalid payload",
            status_code=400,
            code="validation_error",
            details=err.messages,
        ) from err


from .auth import LoginSchema, RegisterSchema  # noqa: E402,F401
