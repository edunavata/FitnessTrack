"""User resource schemas."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, validate


class UserCreateSchema(Schema):
    """Payload for creating a new user from the admin surface."""

    email = fields.Email(required=True, validate=validate.Length(max=254))
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    full_name = fields.String(load_default=None, validate=validate.Length(max=100))


class UserFilterSchema(Schema):
    """Supported query parameters for listing users."""

    class Meta:
        unknown = EXCLUDE

    email = fields.String(load_default=None, validate=validate.Length(min=1, max=254))
    username = fields.String(load_default=None, validate=validate.Length(min=1, max=50))


class UserSchema(Schema):
    """Public representation of a user entity."""

    id = fields.Integer(required=True)
    email = fields.Email(required=True)
    username = fields.String(required=True)
    full_name = fields.String(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
