"""Centralized JSON (RFC 7807) error handling for the API."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any, cast
from uuid import uuid4

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

# Optional integrations (guarded imports)
try:
    from marshmallow import ValidationError as MarshmallowValidationError
except Exception:  # pragma: no cover
    MarshmallowValidationError = None

try:
    from sqlalchemy.exc import IntegrityError, OperationalError
except Exception:  # pragma: no cover
    IntegrityError = OperationalError = None

log = logging.getLogger(__name__)


def _ensure_request_id() -> str:
    """
    Get or generate a request-scoped correlation identifier.

    The function reads standard correlation headers and falls back
    to a newly generated UUID4. The value is stored in ``g.request_id``.

    :returns: Correlation/request identifier.
    :rtype: str
    """
    if hasattr(g, "request_id"):
        return cast(str, g.request_id)

    hdr = request.headers.get("X-Request-Id") or request.headers.get("X-Correlation-Id")
    req_id = hdr or str(uuid4())
    g.request_id = req_id
    return req_id


def _http_status_to_code(status_code: int) -> str:
    """Map common HTTP status codes to canonical, stable error codes."""
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        413: "payload_too_large",
        415: "unsupported_media_type",
        422: "unprocessable_entity",
        429: "too_many_requests",
        500: "internal_server_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, "error")


def _as_problem(
    *,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build an RFC 7807 Problem Details dict.

    :param status: HTTP status code.
    :param code: Stable machine-consumable error code.
    :param message: Human-readable error summary (safe for clients).
    :param details: Optional safe, structured details.
    :returns: Problem+JSON dictionary.
    :rtype: dict
    """
    instance = request.path if request else None
    problem = {
        "type": "about:blank",  # you may replace with canonical docs URL per error type
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": message,
        "instance": instance,
        "code": code,  # custom field retained from your original contract
    }
    if details:
        problem["details"] = details
    # Always attach correlation id
    problem["request_id"] = _ensure_request_id()
    return problem


def _problem_response(problem: dict[str, Any]) -> Response:
    """
    Return a Flask response with ``application/problem+json`` media type.

    :param problem: Problem details payload.
    :returns: Flask JSON Response with proper MIME type.
    :rtype: flask.Response
    """
    resp = jsonify(problem)
    resp.mimetype = "application/problem+json"
    return resp


class APIError(Exception):
    """
    Represent a JSON-serializable API error.

    Parameters
    ----------
    message : str
        Human-readable description presented to clients.
    status_code : int, optional
        HTTP status code to return. Defaults to ``400``.
    code : str, optional
        Machine-readable identifier, typically snake_case. Defaults to
        ``"bad_request"``.
    details : dict[str, Any] | None, optional
        Optional structured payload (e.g., validation messages) included in the
        response body.

    Attributes
    ----------
    message : str
        Error summary stored for serialization.
    status_code : int
        HTTP status code returned to the client.
    code : str
        Stable machine-readable identifier.
    details : dict[str, Any]
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
        self.status_code = int(status_code)
        self.code = code
        self.details = details or {}

    def to_problem(self) -> dict[str, Any]:
        """
        Serialize error metadata into an RFC 7807 problem.

        :returns: Problem details dictionary.
        :rtype: dict
        """
        return _as_problem(
            status=self.status_code,
            code=self.code,
            message=self.message,
            details=self.details or None,
        )


# Domain conveniences
class NotFound(APIError):
    """404 when resources are missing."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=HTTPStatus.NOT_FOUND, code="not_found")


class Conflict(APIError):
    """409 for uniqueness/constraint collisions."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=HTTPStatus.CONFLICT, code="conflict")


class Unauthorized(APIError):
    """401 when authentication fails."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=HTTPStatus.UNAUTHORIZED, code="unauthorized")


class Forbidden(APIError):
    """403 when authorization denies access."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=HTTPStatus.FORBIDDEN, code="forbidden")


def init_app(app: Flask) -> None:
    """
    Attach JSON error handlers to the Flask app.

    Notes
    -----
    - Guarantees RFC 7807 responses for all handled errors.
    - Ensures a correlation ``request_id`` is present on every error.
    - Emits 5xx with ``exc_info`` for traceability; 4xx as warnings.
    """

    @app.before_request
    def _seed_request_id() -> None:
        """Seed request id early for logs and downstream usage."""
        _ensure_request_id()

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        problem = err.to_problem()
        # 4xx → warning; 5xx → error (unlikely via APIError but kept for consistency)
        level = log.error if err.status_code >= 500 else log.warning
        level(
            "APIError: code=%s status=%s msg=%s request_id=%s",
            err.code,
            err.status_code,
            err.message,
            problem.get("request_id"),
        )
        return _problem_response(problem), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        status = int(err.code or HTTPStatus.INTERNAL_SERVER_ERROR)
        error_code = _http_status_to_code(status)
        # Werkzeug may provide HTML-ish description; normalize for clients
        message = (err.description or error_code.replace("_", " ").capitalize()).strip()
        if status == HTTPStatus.NOT_FOUND and request:
            message = f"Route '{request.path}' not found"
        problem = _as_problem(status=status, code=error_code, message=message)
        level = log.error if status >= 500 else log.warning
        # Avoid leaking tracebacks for expected HTTP errors (no exc_info)
        level(
            "HTTPException: code=%s status=%s detail=%s request_id=%s",
            error_code,
            status,
            message,
            problem.get("request_id"),
        )
        return _problem_response(problem), status

    # Optional: schema validation (Marshmallow)
    if MarshmallowValidationError is not None:

        @app.errorhandler(MarshmallowValidationError)
        def handle_validation_error(err: Any):
            # err.messages is a dict[str, list[str]] typically
            problem = _as_problem(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                code="validation_error",
                message="Validation failed",
                details={
                    "errors": getattr(err, "messages", None)
                    or getattr(err, "normalized_messages", lambda: None)()
                },
            )
            log.warning("ValidationError: request_id=%s", problem.get("request_id"))
            return _problem_response(problem), HTTPStatus.UNPROCESSABLE_ENTITY

    # Optional: database errors (SQLAlchemy)
    if IntegrityError is not None:

        @app.errorhandler(IntegrityError)
        def handle_integrity_error(err: Any):
            # Do not leak raw DB error to clients
            problem = _as_problem(
                status=HTTPStatus.CONFLICT,
                code="conflict",
                message="Resource conflict",
            )
            # Log root cause with traceback for operators
            log.error(
                "IntegrityError: request_id=%s",
                problem.get("request_id"),
                exc_info=True,
            )
            return _problem_response(problem), HTTPStatus.CONFLICT

    if OperationalError is not None:

        @app.errorhandler(OperationalError)
        def handle_operational_error(err: Any):
            # E.g., transient DB connectivity, deadlocks, etc.
            problem = _as_problem(
                status=HTTPStatus.SERVICE_UNAVAILABLE,
                code="service_unavailable",
                message="Service temporarily unavailable",
            )
            log.error(
                "OperationalError: request_id=%s",
                problem.get("request_id"),
                exc_info=True,
            )
            return _problem_response(problem), HTTPStatus.SERVICE_UNAVAILABLE

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        # Unexpected server-side error; never leak internal details
        problem = _as_problem(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="internal_server_error",
            message="Unexpected error",
            details=None,
        )
        # Attach a short id inside details for human support if desired
        # (we already expose request_id; keeping minimal additional surface)
        log.error(
            "Unhandled exception: request_id=%s",
            problem.get("request_id"),
            exc_info=True,
        )
        return _problem_response(problem), HTTPStatus.INTERNAL_SERVER_ERROR
