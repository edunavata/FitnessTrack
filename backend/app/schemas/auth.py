"""Marshmallow schemas used by authentication endpoints."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    """Validate payloads submitted to the registration endpoint.

    Notes
    -----
    Requires ``email`` and ``password`` fields; passwords must be at least
    eight characters long but are not otherwise constrained.
    """

    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))


class LoginSchema(Schema):
    """Validate payloads submitted to the login endpoint."""

    email = fields.Email(required=True)
    password = fields.String(required=True)
