"""RFC 7807 / RFC 9457 problem helpers for the API layer."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


def problem(
    *,
    status: int,
    title: str | None = None,
    detail: str | None = None,
    type: str = "about:blank",
    instance: str | None = None,
    code: str | None = None,
    errors: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> Response:
    """Build a Flask ``Response`` carrying Problem Details JSON.

:param status: HTTP status code to emit.
:type status: int
:param title: Optional short summary of the problem.
:type title: str | None
:param detail: Extended explanation for clients.
:type detail: str | None
:param type: Canonical URI describing the problem type.
:type type: str
:param instance: URI reference that identifies the specific occurrence.
:type instance: str | None
:param code: Optional application error code.
:type code: str | None
:param errors: Structured validation details (list or mapping).
:type errors: list[dict[str, Any]] | dict[str, Any] | None
:returns: Flask response carrying ``application/problem+json`` payload.
:rtype: flask.Response
"""

    status_enum = HTTPStatus(status)
    payload: dict[str, Any] = {
        "type": type,
        "title": title or status_enum.phrase,
        "status": status_enum.value,
        "detail": detail,
        "instance": instance or (request.path if request else None),
    }
    if code:
        payload["code"] = code
    if errors:
        payload["errors"] = errors
    response = jsonify(payload)
    response.status_code = status_enum.value
    response.mimetype = "application/problem+json"
    return response


def _handle_validation_error(err: ValidationError) -> Response:
    """Convert Marshmallow validation errors into Problem Details responses.

:param err: Validation error raised by Marshmallow.
:type err: marshmallow.ValidationError
:returns: Problem details response with ``422 Unprocessable Entity``.
:rtype: flask.Response
"""

    return problem(
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
        title="Validation Failed",
        detail="Request body validation failed.",
        code="validation_error",
        errors=getattr(err, "messages", None),
    )


def register_problem_handlers(bp: Blueprint) -> None:
    """Attach default Problem Details handlers to a blueprint.

:param bp: Blueprint receiving handlers.
:type bp: flask.Blueprint
"""

    @bp.errorhandler(HTTPException)
    def _http_exception_handler(err: HTTPException) -> Response:
        status = int(err.code or HTTPStatus.INTERNAL_SERVER_ERROR)
        title = (err.name or HTTPStatus(status).phrase).strip()
        detail = getattr(err, "description", None)
        code = current_app.config.get("API_ERROR_CODE_MAP", {}).get(status)
        return problem(status=status, title=title, detail=detail, code=code)

    @bp.errorhandler(ValidationError)
    def _marshmallow_error_handler(err: ValidationError) -> Response:
        return _handle_validation_error(err)

    @bp.errorhandler(Exception)
    def _unhandled_error_handler(err: Exception) -> Response:
        current_app.logger.exception("Unhandled API error", exc_info=err)
        return problem(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
            detail="Unexpected error while processing the request.",
            code="internal_server_error",
        )
