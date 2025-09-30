# app/core/errors.py
"""Centralized JSON error handling for the API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Represent a JSON-serializable API error.

    Parameters
    ----------
    message: str
        Human-readable description presented to clients.
    status_code: int, optional
        HTTP status code to return. Defaults to ``400``.
    code: str, optional
        Machine-readable identifier, typically snake_case. Defaults to
        ``"bad_request"``.
    details: dict[str, Any] | None, optional
        Optional structured payload (e.g., validation messages) included in the
        response body.

    Attributes
    ----------
    message: str
        Error summary stored for serialization.
    status_code: int
        HTTP status code returned to the client.
    code: str
        Stable machine-readable identifier.
    details: dict[str, Any]
        Arbitrary context specific to the error instance.
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
        """Serialize error metadata into a response-friendly dictionary."""
        data: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            data["details"] = self.details
        return data


# Convenience domain errors (extend as needed)
class NotFound(APIError):
    """Specialization for 404 responses when resources are missing."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404, code="not_found")


class Conflict(APIError):
    """Conflict error raised when unique constraints are violated."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409, code="conflict")


class Unauthorized(APIError):
    """Unauthorized error used when authentication fails."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401, code="unauthorized")


class Forbidden(APIError):
    """Forbidden error used when authorization checks deny access."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403, code="forbidden")


def _http_status_to_code(status_code: int) -> str:
    """Map common HTTP status codes to canonical error codes."""
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


def init_app(app: Flask) -> None:
    """Attach JSON error handlers to the Flask app.

    Parameters
    ----------
    app: flask.Flask
        Application receiving error handlers.

    Notes
    -----
    - Ensures all errors, including uncaught exceptions, produce JSON
      responses.
    - Generates a correlation ``id`` for unexpected errors to ease debugging.
    - The unexpected error handler emits full stack traces to the application
      logger at ``ERROR`` level.
    """

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        payload = {"error": err.to_dict()}
        return jsonify(payload), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
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
