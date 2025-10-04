"""Workout endpoints."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.deps import (
    build_cached_response,
    enforce_idempotency,
    json_response,
    parse_pagination,
    require_auth,
    store_idempotent_response,
    timing,
)
from app.api.etag import set_response_etag
from app.schemas import WorkoutCreateSchema, WorkoutSchema, build_meta
from app.schemas.workout import WorkoutFilterSchema
from app.services.workout_service import WorkoutService

bp = Blueprint("workouts", __name__, url_prefix="/workouts")

workout_schema = WorkoutSchema()
workout_list_schema = WorkoutSchema(many=True)
workout_create_schema = WorkoutCreateSchema()
workout_filter_schema = WorkoutFilterSchema()


@bp.get("")
@require_auth
@timing
def list_workouts():
    """Return paginated workouts."""

    filters = workout_filter_schema.load(request.args)
    pagination = parse_pagination()
    service = WorkoutService()
    items, total = service.list_workouts(filters, pagination)
    data = workout_list_schema.dump(items)
    meta = build_meta(total=total, page=pagination.page, limit=pagination.limit)
    return json_response({"data": data, "meta": meta})


@bp.post("")
@require_auth
@timing
def create_workout():
    """Create a new workout session."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = enforce_idempotency(idempotency_key)
    if is_replay and cached:
        return build_cached_response(cached)
    payload = workout_create_schema.load(request.get_json(silent=True) or {})
    service = WorkoutService()
    workout = service.create_workout(payload)
    body = {"data": workout_schema.dump(workout)}
    response = json_response(body, status=201)
    set_response_etag(response, workout)
    store_idempotent_response(
        idempotency_key,
        {
            "body": body,
            "status": 201,
            "headers": {
                "ETag": response.headers.get("ETag"),
                "Content-Type": response.mimetype,
            },
        },
    )
    return response
