"""API v1 blueprint registration."""

from __future__ import annotations

from flask import Blueprint

bp_v1 = Blueprint("api_v1", __name__)


def _register_blueprints() -> None:
    from . import auth, exercises, health, routines, subjects, users, workouts

    bp_v1.register_blueprint(health.bp)
    bp_v1.register_blueprint(auth.bp)
    bp_v1.register_blueprint(users.bp)
    bp_v1.register_blueprint(exercises.bp)
    bp_v1.register_blueprint(routines.bp)
    bp_v1.register_blueprint(workouts.bp)
    bp_v1.register_blueprint(subjects.bp)


_register_blueprints()

__all__ = ["bp_v1"]
