"""Utilities for registering grouped API blueprints."""

from __future__ import annotations

from collections.abc import Iterable

from flask import Blueprint, Flask


def register_blueprint_group(
    app: Flask,
    *,
    base_prefix: str,
    entries: Iterable[tuple[Blueprint, str]],
) -> None:
    """Register a group of blueprints under a shared URL prefix.

    Parameters
    ----------
    app: Flask
        Application that will receive the blueprints.
    base_prefix: str
        Base path such as ``/api/v1`` prepended to each blueprint entry.
    entries: Iterable[tuple[Blueprint, str]]
        Blueprint and relative prefix pairs to be attached.

    Notes
    -----
    Slashes in ``base_prefix`` and relative prefixes are normalized to avoid
    duplicate separators when registering.
    """
    for bp, rel_prefix in entries:
        # Normalize slashes safely
        full_prefix = "/".join(
            seg for seg in [base_prefix.rstrip("/"), rel_prefix.strip("/")] if seg
        )
        full_prefix = "/" + full_prefix if not full_prefix.startswith("/") else full_prefix
        app.register_blueprint(bp, url_prefix=full_prefix)
