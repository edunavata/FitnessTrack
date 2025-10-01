"""Authentication endpoints using JWT access tokens."""

from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from app.core.errors import Conflict, Unauthorized
from app.core.extensions import db
from app.models.user import User
from app.schemas import LoginSchema, RegisterSchema, load_data

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    """Register a new account and persist hashed credentials.

    Returns
    -------
    tuple[dict[str, int | str], int]
        JSON payload containing the newly created user's ``id``, ``email`` and
        ``name`` plus the ``201 Created`` status code.

    Raises
    ------
    Conflict
        If another user already exists with the submitted email address.

    Notes
    -----
    - Request payload must include ``name``, ``email`` and ``password`` fields
      that pass :class:`app.schemas.RegisterSchema` validation.
    - Passwords are hashed via :meth:`app.models.user.User.password` before
      persistence; no plain text storage occurs.
    """
    data = load_data(RegisterSchema(), request.get_json() or {})
    name = data["name"]
    email = data["email"]
    password = data["password"]
    if User.query.filter_by(email=email).first() is not None:
        raise Conflict("Email already registered")

    user = User(email=email, name=name)
    user.password = password
    db.session.add(user)
    db.session.commit()
    return {"id": user.id, "email": user.email, "name": user.name}, 201


@bp.post("/login")
def login():
    """Authenticate credentials and issue a JWT access token.

    Returns
    -------
    dict[str, str]
        JSON payload with an ``access_token`` encoded by
        :func:`flask_jwt_extended.create_access_token`.

    Raises
    ------
    Unauthorized
        If the email is unknown or the password verification fails.

    Notes
    -----
    Requests are validated using :class:`app.schemas.LoginSchema`. The route
    does not throttle attempts, so clients should implement their own retry
    handling.
    """
    data = load_data(LoginSchema(), request.get_json() or {})
    email = data["email"]
    password = data["password"]

    user = User.query.filter_by(email=email).first()
    if user is None or not user.verify_password(password):
        raise Unauthorized("Invalid credentials")

    token = create_access_token(identity=user.id)
    return {"access_token": token}


@bp.get("/me")
@jwt_required()
def me():
    """Return the authenticated user's profile details.

    Returns
    -------
    dict[str, int | str]
        JSON payload exposing the current user's ``id``, ``email`` and ``name``.

    Raises
    ------
    Unauthorized
        If the JWT identity is missing or does not correspond to a persisted
        user.

    Notes
    -----
    Requires a valid ``Authorization: Bearer`` header produced by the login
    endpoint. The handler performs a database lookup on each call and does not
    cache results.
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user is None:
        raise Unauthorized("User not found")
    return {"id": user.id, "email": user.email, "name": user.name}
