"""Workout resource schemas."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, validate


class WorkoutCreateSchema(Schema):
    """Payload for creating a workout session."""

    subject_id = fields.Integer(required=True)
    workout_date = fields.DateTime(required=True)
    status = fields.String(load_default="PENDING")
    routine_day_id = fields.Integer(load_default=None)
    cycle_id = fields.Integer(load_default=None)
    location = fields.String(load_default=None, validate=validate.Length(max=120))
    perceived_fatigue = fields.Integer(load_default=None)
    bodyweight_kg = fields.Float(load_default=None)
    notes = fields.String(load_default=None)


class WorkoutFilterSchema(Schema):
    """Query parameters accepted by the workouts list endpoint."""

    class Meta:
        unknown = EXCLUDE

    subject_id = fields.Integer(load_default=None)
    status = fields.String(load_default=None)
    date_from = fields.DateTime(load_default=None)
    date_to = fields.DateTime(load_default=None)


class WorkoutSchema(Schema):
    """Representation of the workout session entity."""

    id = fields.Integer(required=True)
    subject_id = fields.Integer(required=True)
    workout_date = fields.DateTime(required=True)
    status = fields.String(required=True)
    routine_day_id = fields.Integer(allow_none=True)
    cycle_id = fields.Integer(allow_none=True)
    location = fields.String(allow_none=True)
    perceived_fatigue = fields.Integer(allow_none=True)
    bodyweight_kg = fields.Float(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
