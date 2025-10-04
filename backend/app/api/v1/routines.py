"""Routine endpoints."""

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
from app.schemas import RoutineCreateSchema, RoutineSchema, build_meta
from app.schemas.routine import RoutineFilterSchema
from app.services.routine_service import RoutineService

bp = Blueprint("routines", __name__, url_prefix="/routines")

routine_schema = RoutineSchema()
routine_list_schema = RoutineSchema(many=True)
routine_create_schema = RoutineCreateSchema()
routine_filter_schema = RoutineFilterSchema()


@bp.get("")
@require_auth
@timing
def list_routines():
    """Return paginated routines."""

    filters = routine_filter_schema.load(request.args)
    pagination = parse_pagination()
    service = RoutineService()
    items, total = service.list_routines(filters, pagination)
    data = routine_list_schema.dump(items)
    meta = build_meta(total=total, page=pagination.page, limit=pagination.limit)
    return json_response({"data": data, "meta": meta})


@bp.post("")
@require_auth
@timing
def create_routine():
    """Create a new routine."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = enforce_idempotency(idempotency_key)
    if is_replay and cached:
        return build_cached_response(cached)
    payload = routine_create_schema.load(request.get_json(silent=True) or {})
    service = RoutineService()
    routine = service.create_routine(payload)
    body = {"data": routine_schema.dump(routine)}
    response = json_response(body, status=201)
    set_response_etag(response, routine)
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
