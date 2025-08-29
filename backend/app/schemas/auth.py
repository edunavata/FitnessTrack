"""Schemas for authentication endpoints."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    """Validate payload for user registration."""

    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))


class LoginSchema(Schema):
    """Validate payload for user login."""

    email = fields.Email(required=True)
    password = fields.String(required=True)
