"""Version 1 API blueprint registry."""

from __future__ import annotations

from flask import Blueprint

API_VERSION = "v1"

# Import blueprints *only here* to keep imports localized and avoid cycles.
from .auth import bp as auth_bp  # noqa: E402
from .health import bp as health_bp  # noqa: E402

# Each tuple: (blueprint, url_prefix_relative_to_version)
REGISTRY: list[tuple[Blueprint, str]] = [
    (health_bp, ""),  # -> /api/v1
    (auth_bp, "/auth"),  # -> /api/v1/auth
]
