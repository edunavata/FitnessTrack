"""Subject endpoints."""

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
from app.schemas import SubjectCreateSchema, SubjectSchema, build_meta
from app.schemas.subject import SubjectFilterSchema
from app.services.subject_service import SubjectService

bp = Blueprint("subjects", __name__, url_prefix="/subjects")

subject_schema = SubjectSchema()
subject_list_schema = SubjectSchema(many=True)
subject_create_schema = SubjectCreateSchema()
subject_filter_schema = SubjectFilterSchema()


@bp.get("")
@require_auth
@timing
def list_subjects():
    """Return paginated subjects."""

    filters = subject_filter_schema.load(request.args)
    pagination = parse_pagination()
    service = SubjectService()
    items, total = service.list_subjects(filters, pagination)
    data = subject_list_schema.dump(items)
    meta = build_meta(total=total, page=pagination.page, limit=pagination.limit)
    return json_response({"data": data, "meta": meta})


@bp.post("")
@require_auth
@timing
def create_subject():
    """Create a new subject."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = enforce_idempotency(idempotency_key)
    if is_replay and cached:
        return build_cached_response(cached)
    payload = subject_create_schema.load(request.get_json(silent=True) or {})
    service = SubjectService()
    subject = service.create_subject(payload)
    body = {"data": subject_schema.dump(subject)}
    response = json_response(body, status=201)
    set_response_etag(response, subject)
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
