"""API blueprint package aggregating versioned endpoints."""

from __future__ import annotations

from collections.abc import Iterable

from flask import Blueprint, Flask


def register_blueprint_group(
    app: Flask,
    *,
    base_prefix: str,
    entries: Iterable[tuple[Blueprint, str]],
) -> None:
    """Register related blueprints beneath a common prefix.

    Parameters
    ----------
    app:
        Application instance receiving the blueprints.
    base_prefix:
        Prefix applied to all entries, typically the API version segment such
        as ``"/api/v1"``.
    entries:
        Iterable of ``(blueprint, relative_prefix)`` pairs where
        ``relative_prefix`` is appended to ``base_prefix``.

    Notes
    -----
    Empty relative prefixes are supported, allowing a blueprint to mount at the
    version root while others extend it with additional path segments.
    """

    for bp, rel_prefix in entries:
        full_prefix = "/".join(
            segment for segment in [base_prefix.rstrip("/"), rel_prefix.strip("/")] if segment
        )
        full_prefix = "/" + full_prefix if not full_prefix.startswith("/") else full_prefix
        app.register_blueprint(bp, url_prefix=full_prefix)


def init_app(app: Flask) -> None:
    """Register the available API versions on the Flask app."""

    api_base = app.config.get("API_BASE_PREFIX", "/api")

    from app.api.v1 import API_VERSION as V1
    from app.api.v1 import REGISTRY as V1_REGISTRY

    register_blueprint_group(app, base_prefix=f"{api_base}/{V1}", entries=V1_REGISTRY)

    # Future:
    # from app.api.v2 import API_VERSION as V2, REGISTRY as V2_REGISTRY
    # register_blueprint_group(app, base_prefix=f"{api_base}/{V2}", entries=V2_REGISTRY)


__all__ = ["init_app", "register_blueprint_group"]
