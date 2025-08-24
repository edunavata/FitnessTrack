# app/core/errors.py
"""Centralized JSON error handling for the API."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base API error for domain/business errors.

    Parameters
    ----------
    message:
        Human-readable error message.
    status_code:
        HTTP status code.
    error_type:
        Machine-readable error type (snake_case).
    fields:
        Optional field-level errors for validation scenarios.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_type: str = "bad_request",
        fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.fields = fields or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error to a standard dict."""
        data: Dict[str, Any] = {
            "type": self.error_type,
            "message": self.message,
            "status": self.status_code,
        }
        if self.fields:
            data["fields"] = self.fields
        return data


# Convenience domain errors (extend as needed)
class NotFound(APIError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404, error_type="not_found")


class Conflict(APIError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409, error_type="conflict")


class Unauthorized(APIError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401, error_type="unauthorized")


class Forbidden(APIError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403, error_type="forbidden")


def _http_status_to_type(status_code: int) -> str:
    """Map common HTTP status codes to error type strings."""
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
    """Attach JSON error handlers to the Flask app.

    Notes
    -----
    - Ensures *all* errors are returned as JSON (no HTML error pages).
    - Adds a correlation `id` for 5xx errors in responses & logs.
    """

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        payload = {"error": err.to_dict()}
        return jsonify(payload), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        # Normalize Werkzeug exceptions (e.g., 404, 405, JSON decode 400, etc.)
        status = err.code or 500
        error_type = _http_status_to_type(status)
        message = err.description or error_type.replace("_", " ").capitalize()

        # Add context for not_found
        if status == 404:
            message = f"Route '{request.path}' not found"

        payload = {"error": {"type": error_type, "message": message, "status": status}}
        return jsonify(payload), status

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        # Generate correlation id for logs and client
        err_id = str(uuid4())
        logging.exception("Unhandled error (id=%s)", err_id)
        payload = {
            "error": {
                "type": "internal_server_error",
                "message": "Unexpected error",
                "status": 500,
                "id": err_id,
            }
        }
        return jsonify(payload), 500
