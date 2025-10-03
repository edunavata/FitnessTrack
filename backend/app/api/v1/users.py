"""User resource endpoints."""

from __future__ import annotations

from http import HTTPStatus

from flask import Response, request, url_for

from app.models.subject import Subject
from app.models.user import User

from .. import deps
from ..errors import problem
from ..etag import set_response_etag, verify_etag
from ..schemas import UserCreateSchema, UserSchema, UserUpdateSchema
from . import api_v1

user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema(partial=True)


@api_v1.get("/users")
@deps.timing
def list_users() -> Response:
    """List users with pagination, filtering, and sorting.

    :returns: JSON response containing the standard pagination envelope.
    :rtype: flask.Response
    """

    # Build the base query and apply client-provided filters.
    pagination = deps.parse_pagination()
    # Acquire a session for database work.
    session = deps.get_session()
    query = session.query(User)

    email = request.args.get("email")
    username = request.args.get("username")
    if email:
        query = query.filter(User.email == email)
    if username:
        query = query.filter(User.username == username)

    sort_map = {
        "id": User.id,
        "created_at": User.created_at,
        "username": User.username,
    }
    query = deps.apply_sorting(query, sort_map, pagination.sort)

    items, total = deps.paginate_query(query, pagination)
    payload = {
        "items": users_schema.dump(items),
        "page": pagination.page,
        "limit": pagination.limit,
        "total": total,
    }
    return deps.json_response(payload)


@api_v1.get("/users/<int:user_id>")
@deps.timing
def retrieve_user(user_id: int) -> Response:
    """Retrieve a single user by identifier.

    :param user_id: Database identifier of the requested user.
    :type user_id: int
    :returns: Serialized user payload with ETag header.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Fetch the requested user or produce a 404 problem response.
    user = session.get(User, user_id)
    if user is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="User not found.", code="not_found")
    response = deps.json_response(user_schema.dump(user))
    return set_response_etag(response, user)


@api_v1.post("/users")
@deps.require_auth
@deps.require_scope("users:write")
@deps.timing
def create_user() -> Response:
    """Create a new user after validating the payload.

    The handler expects an ``Idempotency-Key`` header so safe retries can
    reuse prior results. Passwords are hashed using the model helper.

    :returns: Newly created user document with ``201 Created``.
    :rtype: flask.Response
    """

    # Enforce idempotency semantics before mutating state.
    idempotency_key = request.headers.get("Idempotency-Key")
    is_replay, cached = deps.enforce_idempotency(idempotency_key)
    if is_replay and cached is not None:
        return deps.build_cached_response(cached)

    payload = request.get_json(silent=True) or {}
    data = user_create_schema.load(payload)
    # Acquire a session for database work.
    session = deps.get_session()

    user = User(
        email=data["email"],
        username=data["username"],
        full_name=data.get("full_name"),
    )
    user.password = data["password"]

    session.add(user)

    subject_id = data.get("subject_id")
    if subject_id is not None:
        subject = session.get(Subject, subject_id)
        if subject is None:
            return problem(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail="Subject not found for provided subject_id.",
                code="subject_not_found",
            )
        subject.user = user

    session.commit()
    body = user_schema.dump(user)
    response = deps.json_response(body, status=HTTPStatus.CREATED)
    set_response_etag(response, user)
    response.headers["Location"] = url_for("api_v1.retrieve_user", user_id=user.id)
    headers = {"Location": response.headers["Location"]}
    if response.headers.get("ETag"):
        headers["ETag"] = response.headers["ETag"]
    deps.store_idempotent_response(
        idempotency_key,
        {
            "body": body,
            "status": HTTPStatus.CREATED,
            "headers": headers,
        },
    )
    return response


@api_v1.patch("/users/<int:user_id>")
@deps.require_auth
@deps.require_scope("users:write")
@deps.timing
def update_user(user_id: int) -> Response:
    """Partially update an existing user using JSON merge semantics.

    :param user_id: Identifier of the user to mutate.
    :type user_id: int
    :returns: Updated user representation with refreshed ETag.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Fetch the requested user or produce a 404 problem response.
    user = session.get(User, user_id)
    if user is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="User not found.", code="not_found")

    # Require an ETag to protect against lost updates.
    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(user, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    payload = request.get_json(silent=True) or {}
    data = user_update_schema.load(payload)

    if "email" in data:
        user.email = data["email"]
    if "username" in data:
        user.username = data["username"]
    if "full_name" in data:
        user.full_name = data["full_name"]
    if "password" in data:
        user.password = data["password"]

    session.commit()
    response = deps.json_response(user_schema.dump(user))
    return set_response_etag(response, user)


@api_v1.delete("/users/<int:user_id>")
@deps.require_auth
@deps.require_scope("users:write")
@deps.timing
def delete_user(user_id: int) -> Response:
    """Delete a user record.

    :param user_id: Identifier of the user to delete.
    :type user_id: int
    :returns: Empty ``204 No Content`` response on success.
    :rtype: flask.Response
    """

    # Acquire a session for database work.
    session = deps.get_session()
    # Fetch the requested user or produce a 404 problem response.
    user = session.get(User, user_id)
    if user is None:
        return problem(status=HTTPStatus.NOT_FOUND, detail="User not found.", code="not_found")

    # Require an ETag to protect against lost updates.
    if_match = request.headers.get("If-Match")
    if not if_match:
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="Missing If-Match header.", code="missing_if_match")
    if not verify_etag(user, if_match.strip('"')):
        return problem(status=HTTPStatus.PRECONDITION_FAILED, detail="ETag mismatch.", code="etag_mismatch")

    session.delete(user)
    session.commit()
    return Response(status=HTTPStatus.NO_CONTENT)
