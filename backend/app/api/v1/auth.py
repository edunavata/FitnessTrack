"""Authentication endpoints using the service layer."""

from __future__ import annotations

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity

from app.api.deps import (
    build_cached_response,
    enforce_idempotency,
    json_response,
    require_auth,
    store_idempotent_response,
    timing,
)
from app.api.etag import set_response_etag
from app.core.extensions import limiter
from app.schemas import (
    LoginSchema,
    RegisterSchema,
    TokenResponseSchema,
    UserSchema,
    WhoAmISchema,
)
from app.services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")

register_schema = RegisterSchema()
login_schema = LoginSchema()
user_schema = UserSchema()
whoami_schema = WhoAmISchema()
token_schema = TokenResponseSchema()


def _login_rate_limit() -> str:
    return str(current_app.config.get("AUTH_LOGIN_RATE_LIMIT", "5 per minute"))


@bp.post("/register")
@timing
def register():
    """Register a new user and return the created representation."""

    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = enforce_idempotency(idempotency_key)
    if is_replay and cached:
        return build_cached_response(cached)
    payload = register_schema.load(request.get_json(silent=True) or {})
    service = AuthService()
    user = service.register_user(payload)
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


@bp.post("/login")
@limiter.limit(_login_rate_limit)
@timing
def login():
    """Authenticate credentials and issue an access token."""

    data = login_schema.load(request.get_json(silent=True) or {})
    service = AuthService()
    token, _ = service.login(data["email"], data["password"])
    body = {"data": token_schema.dump({"access_token": token})}
    response = json_response(body)
    # TODO: Support idempotent login responses when backed by a shared store.
    return response


@bp.get("/whoami")
@require_auth
@timing
def whoami():
    """Return the authenticated user profile."""

    identity = get_jwt_identity()
    service = AuthService()
    user = service.whoami(identity)
    body = {"data": whoami_schema.dump(user)}
    response = json_response(body)
    set_response_etag(response, user)
    return response
