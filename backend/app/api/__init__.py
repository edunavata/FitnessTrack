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
