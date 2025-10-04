"""User endpoints."""

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
from app.schemas import UserCreateSchema, UserSchema, build_meta
from app.schemas.user import UserFilterSchema
from app.services.user_service import UserService

bp = Blueprint("users", __name__, url_prefix="/users")

user_schema = UserSchema()
user_list_schema = UserSchema(many=True)
user_create_schema = UserCreateSchema()
user_filter_schema = UserFilterSchema()


@bp.get("")
@require_auth
@timing
def list_users():
    """Return paginated users."""

    filters = user_filter_schema.load(request.args)
    pagination = parse_pagination()
    service = UserService()
    items, total = service.list_users(filters, pagination)
    data = user_list_schema.dump(items)
    meta = build_meta(total=total, page=pagination.page, limit=pagination.limit)
    return json_response({"data": data, "meta": meta})


@bp.post("")
@require_auth
@timing
def create_user():
    """Create a new user."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = enforce_idempotency(idempotency_key)
    if is_replay and cached:
        return build_cached_response(cached)
    payload = user_create_schema.load(request.get_json(silent=True) or {})
    service = UserService()
    user = service.create_user(payload)
    body = {"data": user_schema.dump(user)}
    response = json_response(body, status=201)
    set_response_etag(response, user)
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
