"""Structured logging configuration with request correlation."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from flask import Flask, g, has_request_context, request

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_HEADERS = ("X-Request-ID", "X-Correlation-ID")


class JSONFormatter(logging.Formatter):
    """Render log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting logic
        payload: dict[str, Any] = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra_keys = {"endpoint", "elapsed_ms"}
        for key in extra_keys:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


class RequestIdFilter(logging.Filter):
    """Ensure a ``request_id`` attribute is always present on log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.request_id = ensure_request_id() if has_request_context() else None
        return True


def ensure_request_id() -> str:
    """Return the current request identifier, generating one when necessary."""

    if has_request_context():
        if hasattr(g, "request_id"):
            return g.request_id  # type: ignore[return-value]
        for header in CORRELATION_HEADERS:
            value = request.headers.get(header)
            if value:
                g.request_id = value
                return value
        request_id = str(uuid4())
        g.request_id = request_id
        return request_id
    return str(uuid4())


def configure_logging(level: str | int = "INFO") -> None:
    """Configure the root logger with JSON-formatted stdout output."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    level_value: int | str = level
    if isinstance(level, str):
        resolved = logging.getLevelName(level.upper())
        level_value = resolved if isinstance(resolved, int) else level.upper()
    root.setLevel(level_value)


def init_app(app: Flask) -> None:
    """Inject request-id middleware and attach filters to the app logger."""

    app.logger.addFilter(RequestIdFilter())

    @app.before_request
    def _seed_request_id() -> None:  # pragma: no cover - integration glue
        ensure_request_id()

    @app.after_request
    def _inject_response_header(response):  # pragma: no cover - integration glue
        response.headers.setdefault(REQUEST_ID_HEADER, ensure_request_id())
        return response


__all__ = ["configure_logging", "init_app", "ensure_request_id"]
