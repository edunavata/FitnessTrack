"""Schema utilities and exports."""

from __future__ import annotations

from typing import Any, cast

from marshmallow import Schema, ValidationError

from app.core.errors import APIError


def load_data(schema: Schema, data: dict[str, Any]) -> dict[str, Any]:
    """Validate *data* against *schema* and return result.

    Parameters
    ----------
    schema:
        An instance of a Marshmallow :class:`Schema`.
    data:
        The input payload to validate.

    Raises
    ------
    APIError
        If validation fails. Field-level errors are included in ``fields``.
    """
    try:
        return cast(dict[str, Any], schema.load(data))
    except ValidationError as err:  # pragma: no cover - simple pass-through
        raise APIError(
            "Invalid payload",
            status_code=400,
            error_type="validation_error",
            fields=err.messages,
        ) from err


from .auth import LoginSchema, RegisterSchema  # noqa: E402,F401
