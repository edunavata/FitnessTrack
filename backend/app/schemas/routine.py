"""Routine resource schemas."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, validate


class RoutineCreateSchema(Schema):
    """Payload for creating a new routine."""

    owner_subject_id = fields.Integer(required=True)
    name = fields.String(required=True, validate=validate.Length(min=3, max=120))
    description = fields.String(load_default=None)
    is_public = fields.Boolean(load_default=False)


class RoutineFilterSchema(Schema):
    """Query parameters accepted by the routines list endpoint."""

    class Meta:
        unknown = EXCLUDE

    owner_subject_id = fields.Integer(load_default=None)
    is_public = fields.Boolean(load_default=None)
    name = fields.String(load_default=None, validate=validate.Length(min=1, max=120))


class RoutineSchema(Schema):
    """Representation of the routine entity."""

    id = fields.Integer(required=True)
    owner_subject_id = fields.Integer(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    is_public = fields.Boolean(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
