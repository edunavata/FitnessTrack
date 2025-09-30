"""Schema utilities centralizing Marshmallow helpers and exports."""

from __future__ import annotations

from typing import Any, cast

from marshmallow import Schema, ValidationError

from app.core.errors import APIError


def load_data(schema: Schema, data: dict[str, Any]) -> dict[str, Any]:
    """Validate a payload using the provided schema and return the result.

    Parameters
    ----------
    schema: marshmallow.Schema
        Schema instance used to deserialize and validate the payload.
    data: dict[str, Any]
        Raw request payload typically obtained from ``request.get_json``.

    Returns
    -------
    dict[str, Any]
        Deserialized payload produced by ``schema.load``.

    Raises
    ------
    APIError
        If validation fails. Field-level errors are included in ``details``.
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
