# app/core/errors.py
"""Centralize JSON error handling for the HTTP API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Represent domain-level API errors rendered as JSON responses.

    Attributes
    ----------
    message: str
        Human-readable error message displayed to clients.
    status_code: int
        HTTP status returned to the client.
    code: str
        Machine-readable error identifier in ``snake_case``.
    details: dict[str, Any]
        Optional structured metadata for validation or debugging contexts.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "bad_request",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error into a JSON-serializable dictionary.

        Returns
        -------
        dict[str, Any]
            Mapping with ``code`` and ``message`` plus optional ``details``.
        """
        data: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            data["details"] = self.details
        return data


# Convenience domain errors (extend as needed)
class NotFound(APIError):
    """Error used when a requested resource cannot be located."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404, code="not_found")


class Conflict(APIError):
    """Error raised when the request conflicts with existing state."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409, code="conflict")


class Unauthorized(APIError):
    """Error returned when authentication fails or is missing."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401, code="unauthorized")


class Forbidden(APIError):
    """Error raised when a user lacks permission for the action."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403, code="forbidden")


def _http_status_to_code(status_code: int) -> str:
    """Map common HTTP status codes to canonical error codes.

    Parameters
    ----------
    status_code: int
        HTTP status code produced by Werkzeug or Flask.

    Returns
    -------
    str
        Error code string compatible with :class:`APIError` payloads.
    """
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        415: "unsupported_media_type",
        422: "unprocessable_entity",
        429: "too_many_requests",
        500: "internal_server_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, "error")


def register_error_handlers(app: Flask) -> None:
    """Attach JSON error handlers to the Flask application.

    Parameters
    ----------
    app: Flask
        Application instance receiving the error handlers.

    Notes
    -----
    All exceptions are normalized into ``{"error": ...}`` JSON payloads. When
    unexpected errors occur, a correlation identifier is included for log
    correlation.
    """

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        """Return domain errors using their serialized representation."""
        payload = {"error": err.to_dict()}
        return jsonify(payload), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        """Convert Werkzeug HTTP exceptions into JSON responses."""
        # Normalize Werkzeug exceptions (e.g., 404, 405, JSON decode 400, etc.)
        status = err.code or 500
        error_code = _http_status_to_code(status)
        message = err.description or error_code.replace("_", " ").capitalize()

        # Add context for not_found
        if status == 404:
            message = f"Route '{request.path}' not found"

        payload = {"error": {"code": error_code, "message": message}}
        return jsonify(payload), status

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        """Log unexpected errors and return a generic JSON payload."""
        # Generate correlation id for logs and client
        err_id = str(uuid4())
        logging.exception("Unhandled error (id=%s)", err_id)
        payload = {
            "error": {
                "code": "internal_server_error",
                "message": "Unexpected error",
                "details": {"id": err_id},
            }
        }
        return jsonify(payload), 500
