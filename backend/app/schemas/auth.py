"""Marshmallow schemas backing authentication endpoints."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    """Validate incoming registration payloads."""

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=120),
    )
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))


class LoginSchema(Schema):
    """Validate incoming login payloads."""

    email = fields.Email(required=True)
    password = fields.String(required=True)
