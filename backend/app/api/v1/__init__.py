"""API v1 blueprint package bundling versioned routes."""

from __future__ import annotations

from flask import Blueprint

API_VERSION = "v1"

# Import blueprints *only here* to keep imports localized and avoid cycles.
from .auth import bp as auth_bp  # noqa: E402
from .exercises import bp as exercises_bp  # noqa: E402
from .health import bp as health_bp  # noqa: E402
from .routines import bp as routines_bp  # noqa: E402
from .subjects import bp as subjects_bp  # noqa: E402
from .users import bp as users_bp  # noqa: E402
from .workouts import bp as workouts_bp  # noqa: E402

# Each tuple: (blueprint, url_prefix_relative_to_version)
REGISTRY: list[tuple[Blueprint, str]] = [
    (health_bp, ""),  # -> /api/v1
    (auth_bp, "/auth"),  # -> /api/v1/auth
    (users_bp, "/users"),
    (exercises_bp, "/exercises"),
    (routines_bp, "/routines"),
    (workouts_bp, "/workouts"),
    (subjects_bp, "/subjects"),
]
