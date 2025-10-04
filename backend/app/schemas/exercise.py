"""Exercise resource schemas."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, validate


class ExerciseCreateSchema(Schema):
    """Payload for creating a new exercise."""

    name = fields.String(required=True, validate=validate.Length(min=3, max=120))
    slug = fields.String(required=True, validate=validate.Length(min=3, max=140))
    primary_muscle = fields.String(required=True)
    movement = fields.String(required=True)
    mechanics = fields.String(required=True)
    force = fields.String(required=True)
    equipment = fields.String(required=True)
    difficulty = fields.String(load_default="BEGINNER")
    is_active = fields.Boolean(load_default=True)
    cues = fields.String(load_default=None)
    instructions = fields.String(load_default=None)


class ExerciseFilterSchema(Schema):
    """Supported query parameters when listing exercises."""

    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None, validate=validate.Length(min=1, max=120))
    primary_muscle = fields.String(load_default=None)
    equipment = fields.String(load_default=None)
    is_active = fields.Boolean(load_default=None)


class ExerciseSchema(Schema):
    """Representation of the exercise entity."""

    id = fields.Integer(required=True)
    name = fields.String(required=True)
    slug = fields.String(required=True)
    primary_muscle = fields.String(required=True)
    movement = fields.String(required=True)
    mechanics = fields.String(required=True)
    force = fields.String(required=True)
    equipment = fields.String(required=True)
    difficulty = fields.String(required=True)
    is_active = fields.Boolean(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
