"""Authentication endpoints using JWT."""

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
    """Create a user with hashed password."""
    data = load_data(RegisterSchema(), request.get_json() or {})
    email = data["email"]
    password = data["password"]
    if User.query.filter_by(email=email).first() is not None:
        raise Conflict("Email already registered")

    user = User(email=email)
    user.password = password
    db.session.add(user)
    db.session.commit()
    return {"id": user.id, "email": user.email}, 201


@bp.post("/login")
def login():
    """Authenticate user and return a JWT."""
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
    """Return the authenticated user's info."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user is None:
        raise Unauthorized("User not found")
    return {"id": user.id, "email": user.email}
