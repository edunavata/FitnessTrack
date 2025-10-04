"""Subject resource schemas."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields


class SubjectCreateSchema(Schema):
    """Payload for creating a subject entity."""

    user_id = fields.Integer(load_default=None)


class SubjectFilterSchema(Schema):
    """Query parameters accepted by the subjects list endpoint."""

    class Meta:
        unknown = EXCLUDE

    user_id = fields.Integer(load_default=None)


class SubjectSchema(Schema):
    """Representation of the pseudonymous subject entity."""

    id = fields.Integer(required=True)
    user_id = fields.Integer(allow_none=True)
    pseudonym = fields.UUID(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
