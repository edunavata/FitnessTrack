"""API blueprint package."""

from __future__ import annotations

from collections.abc import Iterable

from flask import Blueprint, Flask


def register_blueprint_group(
    app: Flask,
    *,
    base_prefix: str,
    entries: Iterable[tuple[Blueprint, str]],
) -> None:
    """
    Register a group of blueprints under a common base prefix.

    :param app: Flask application.
    :param base_prefix: Base prefix (e.g. '/api/v1').
    :param entries: Iterable of (blueprint, relative_prefix).
    """
    for bp, rel_prefix in entries:
        # Normalize slashes safely
        full_prefix = "/".join(
            seg for seg in [base_prefix.rstrip("/"), rel_prefix.strip("/")] if seg
        )
        full_prefix = "/" + full_prefix if not full_prefix.startswith("/") else full_prefix
        app.register_blueprint(bp, url_prefix=full_prefix)


def init_app(app: Flask) -> None:
    """
    Register all API versions.
    """
    api_base = app.config.get("API_BASE_PREFIX", "/api")

    # v1
    from app.api.v1 import API_VERSION as V1
    from app.api.v1 import REGISTRY as V1_REGISTRY

    register_blueprint_group(app, base_prefix=f"{api_base}/{V1}", entries=V1_REGISTRY)

    # Future:
    # from app.api.v2 import API_VERSION as V2, REGISTRY as V2_REGISTRY
    # register_blueprint_group(app, base_prefix=f"{api_base}/{V2}", entries=V2_REGISTRY)
