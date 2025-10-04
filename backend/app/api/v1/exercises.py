"""Exercise endpoints."""

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
from app.schemas import ExerciseCreateSchema, ExerciseSchema, build_meta
from app.schemas.exercise import ExerciseFilterSchema
from app.services.exercise_service import ExerciseService

bp = Blueprint("exercises", __name__, url_prefix="/exercises")

exercise_schema = ExerciseSchema()
exercise_list_schema = ExerciseSchema(many=True)
exercise_create_schema = ExerciseCreateSchema()
exercise_filter_schema = ExerciseFilterSchema()


@bp.get("")
@timing
def list_exercises():
    """Return paginated exercises."""

    filters = exercise_filter_schema.load(request.args)
    pagination = parse_pagination()
    service = ExerciseService()
    items, total = service.list_exercises(filters, pagination)
    data = exercise_list_schema.dump(items)
    meta = build_meta(total=total, page=pagination.page, limit=pagination.limit)
    return json_response({"data": data, "meta": meta})


@bp.post("")
@require_auth
@timing
def create_exercise():
    """Create a new exercise entry."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = enforce_idempotency(idempotency_key)
    if is_replay and cached:
        return build_cached_response(cached)
    payload = exercise_create_schema.load(request.get_json(silent=True) or {})
    service = ExerciseService()
    exercise = service.create_exercise(payload)
    body = {"data": exercise_schema.dump(exercise)}
    response = json_response(body, status=201)
    set_response_etag(response, exercise)
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
