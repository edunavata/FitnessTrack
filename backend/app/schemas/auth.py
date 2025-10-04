"""Authentication-related Marshmallow schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    """Input payload for account registration."""

    email = fields.Email(required=True, validate=validate.Length(max=254))
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    full_name = fields.String(load_default=None, validate=validate.Length(max=100))


class LoginSchema(Schema):
    """Input payload for authenticating a user."""

    email = fields.Email(required=True, validate=validate.Length(max=254))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))


class TokenResponseSchema(Schema):
    """Response payload containing an access token."""

    access_token = fields.String(required=True)
    token_type = fields.String(load_default="bearer")


class WhoAmISchema(Schema):
    """Response payload exposing identity details for the authenticated user."""

    id = fields.Integer(required=True)
    email = fields.Email(required=True)
    username = fields.String(required=True)
    full_name = fields.String(allow_none=True)
