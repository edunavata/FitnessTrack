"""Marshmallow schemas dedicated to the versioned REST API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from marshmallow import Schema, fields, validate


class BaseSchema(Schema):
    """Base schema enabling ordered output for consistent API responses."""

    class Meta:
        ordered = True


class UserSchema(BaseSchema):
    """Serialize ``User`` instances for API responses."""

    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    username = fields.String(required=True)
    full_name = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    subject_id = fields.Function(lambda obj: getattr(obj, "subject", None) and obj.subject.id, dump_only=True)


class UserCreateSchema(UserSchema):
    """Validate payloads when creating users."""

    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8))
    subject_id = fields.Int(load_only=True, allow_none=True)


class UserUpdateSchema(BaseSchema):
    """Schema for partial user updates."""

    email = fields.Email(load_only=True)
    username = fields.String(load_only=True)
    full_name = fields.String(load_only=True, allow_none=True)
    password = fields.String(load_only=True, validate=validate.Length(min=8))


class SubjectSchema(BaseSchema):
    """Serialize ``Subject`` records."""

    id = fields.Int(dump_only=True)
    user_id = fields.Int(allow_none=True)
    pseudonym = fields.UUID(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class SubjectCreateSchema(BaseSchema):
    """Validate subject creation requests."""

    user_id = fields.Int(load_only=True, allow_none=True)


class SubjectUpdateSchema(BaseSchema):
    """Schema for patching subject data."""

    user_id = fields.Int(load_only=True, allow_none=True)


class SubjectProfileSchema(BaseSchema):
    """Serialize and validate subject profile data."""

    id = fields.Int(dump_only=True)
    subject_id = fields.Int(dump_only=True)
    sex = fields.String(validate=validate.OneOf(["MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"]), allow_none=True)
    birth_year = fields.Int(validate=validate.Range(min=1900, max=date.today().year), allow_none=True)
    height_cm = fields.Int(validate=validate.Range(min=1), allow_none=True)
    dominant_hand = fields.String(validate=validate.Length(max=10), allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class BodyMetricSchema(BaseSchema):
    """Schema for subject body metrics time-series."""

    id = fields.Int(dump_only=True)
    subject_id = fields.Int(dump_only=True)
    measured_on = fields.Date(required=True)
    weight_kg = fields.Decimal(allow_none=True, as_string=True)
    bodyfat_pct = fields.Decimal(allow_none=True, as_string=True)
    resting_hr = fields.Int(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ExerciseSchema(BaseSchema):
    """Serialize exercise catalog entries."""

    id = fields.Int(dump_only=True)
    name = fields.String(required=True)
    slug = fields.String(required=True)
    primary_muscle = fields.String(required=True)
    movement = fields.String(required=True)
    mechanics = fields.String(required=True)
    force = fields.String(required=True)
    unilateral = fields.Bool(required=True)
    equipment = fields.String(required=True)
    grip = fields.String(allow_none=True)
    range_of_motion = fields.String(allow_none=True)
    difficulty = fields.String(required=True)
    cues = fields.String(allow_none=True)
    instructions = fields.String(allow_none=True)
    video_url = fields.String(allow_none=True)
    is_active = fields.Bool(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ExerciseCreateSchema(ExerciseSchema):
    """Validation schema for creating exercises."""

    id = fields.Int(dump_only=True)


class ExerciseUpdateSchema(BaseSchema):
    """Schema for partial exercise updates."""

    name = fields.String(load_only=True)
    slug = fields.String(load_only=True)
    primary_muscle = fields.String(load_only=True)
    movement = fields.String(load_only=True)
    mechanics = fields.String(load_only=True)
    force = fields.String(load_only=True)
    unilateral = fields.Bool(load_only=True)
    equipment = fields.String(load_only=True)
    grip = fields.String(load_only=True, allow_none=True)
    range_of_motion = fields.String(load_only=True, allow_none=True)
    difficulty = fields.String(load_only=True)
    cues = fields.String(load_only=True, allow_none=True)
    instructions = fields.String(load_only=True, allow_none=True)
    video_url = fields.String(load_only=True, allow_none=True)
    is_active = fields.Bool(load_only=True)


class RoutineSchema(BaseSchema):
    """Serialize ``Routine`` templates."""

    id = fields.Int(dump_only=True)
    owner_subject_id = fields.Int(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    is_public = fields.Bool(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class RoutineCreateSchema(RoutineSchema):
    """Schema validating routine creation."""

    pass


class RoutineUpdateSchema(BaseSchema):
    """Schema for partial routine updates."""

    name = fields.String(load_only=True)
    description = fields.String(load_only=True, allow_none=True)
    is_public = fields.Bool(load_only=True)


class RoutineDaySchema(BaseSchema):
    """Serialize routine day entities."""

    id = fields.Int(dump_only=True)
    routine_id = fields.Int(dump_only=True)
    day_index = fields.Int(required=True)
    is_rest = fields.Bool(required=True)
    title = fields.String(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class RoutineDayUpdateSchema(BaseSchema):
    """Schema for routine day updates."""

    day_index = fields.Int(load_only=True)
    is_rest = fields.Bool(load_only=True)
    title = fields.String(load_only=True, allow_none=True)
    notes = fields.String(load_only=True, allow_none=True)


class RoutineDayExerciseSchema(BaseSchema):
    """Serialize exercises scheduled on a routine day."""

    id = fields.Int(dump_only=True)
    routine_day_id = fields.Int(dump_only=True)
    exercise_id = fields.Int(required=True)
    position = fields.Int(required=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class RoutineDayExerciseUpdateSchema(BaseSchema):
    """Schema for updating routine day exercises."""

    exercise_id = fields.Int(load_only=True)
    position = fields.Int(load_only=True)
    notes = fields.String(load_only=True, allow_none=True)


class RoutineExerciseSetSchema(BaseSchema):
    """Serialize planned set targets."""

    id = fields.Int(dump_only=True)
    routine_day_exercise_id = fields.Int(dump_only=True)
    set_index = fields.Int(required=True)
    is_warmup = fields.Bool(required=True)
    to_failure = fields.Bool(required=True)
    target_weight_kg = fields.Decimal(allow_none=True, as_string=True)
    target_reps = fields.Int(allow_none=True)
    target_rir = fields.Int(allow_none=True)
    target_rpe = fields.Decimal(allow_none=True, as_string=True)
    target_tempo = fields.String(allow_none=True)
    target_rest_s = fields.Int(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class RoutineExerciseSetUpdateSchema(BaseSchema):
    """Schema for updating planned sets."""

    set_index = fields.Int(load_only=True)
    is_warmup = fields.Bool(load_only=True)
    to_failure = fields.Bool(load_only=True)
    target_weight_kg = fields.Decimal(load_only=True, allow_none=True, as_string=True)
    target_reps = fields.Int(load_only=True, allow_none=True)
    target_rir = fields.Int(load_only=True, allow_none=True)
    target_rpe = fields.Decimal(load_only=True, allow_none=True, as_string=True)
    target_tempo = fields.String(load_only=True, allow_none=True)
    target_rest_s = fields.Int(load_only=True, allow_none=True)
    notes = fields.String(load_only=True, allow_none=True)


class SubjectRoutineSchema(BaseSchema):
    """Serialize links between subjects and routines."""

    id = fields.Int(dump_only=True)
    subject_id = fields.Int(required=True)
    routine_id = fields.Int(required=True)
    is_active = fields.Bool(required=True)
    saved_on = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CycleSchema(BaseSchema):
    """Serialize routine execution cycles."""

    id = fields.Int(dump_only=True)
    subject_id = fields.Int(required=True)
    routine_id = fields.Int(required=True)
    cycle_number = fields.Int(required=True)
    started_on = fields.Date(allow_none=True)
    ended_on = fields.Date(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CycleUpdateSchema(BaseSchema):
    """Schema for partial cycle updates."""

    started_on = fields.Date(load_only=True, allow_none=True)
    ended_on = fields.Date(load_only=True, allow_none=True)
    notes = fields.String(load_only=True, allow_none=True)


class WorkoutSessionSchema(BaseSchema):
    """Serialize performed workout sessions."""

    id = fields.Int(dump_only=True)
    subject_id = fields.Int(required=True)
    workout_date = fields.DateTime(required=True)
    status = fields.String(required=True)
    routine_day_id = fields.Int(allow_none=True)
    cycle_id = fields.Int(allow_none=True)
    location = fields.String(allow_none=True)
    perceived_fatigue = fields.Int(allow_none=True)
    bodyweight_kg = fields.Decimal(allow_none=True, as_string=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class WorkoutSessionUpdateSchema(BaseSchema):
    """Schema for updating workout sessions."""

    workout_date = fields.DateTime(load_only=True)
    status = fields.String(load_only=True)
    routine_day_id = fields.Int(load_only=True, allow_none=True)
    cycle_id = fields.Int(load_only=True, allow_none=True)
    location = fields.String(load_only=True, allow_none=True)
    perceived_fatigue = fields.Int(load_only=True, allow_none=True)
    bodyweight_kg = fields.Decimal(load_only=True, allow_none=True, as_string=True)
    notes = fields.String(load_only=True, allow_none=True)


class ExerciseSetLogSchema(BaseSchema):
    """Serialize performed exercise sets."""

    id = fields.Int(dump_only=True)
    subject_id = fields.Int(required=True)
    exercise_id = fields.Int(required=True)
    session_id = fields.Int(allow_none=True)
    planned_set_id = fields.Int(allow_none=True)
    performed_at = fields.DateTime(required=True)
    set_index = fields.Int(required=True)
    is_warmup = fields.Bool(required=True)
    to_failure = fields.Bool(required=True)
    actual_weight_kg = fields.Decimal(allow_none=True, as_string=True)
    actual_reps = fields.Int(allow_none=True)
    actual_rir = fields.Int(allow_none=True)
    actual_rpe = fields.Decimal(allow_none=True, as_string=True)
    actual_tempo = fields.String(allow_none=True)
    actual_rest_s = fields.Int(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ExerciseSetLogUpdateSchema(BaseSchema):
    """Schema for updating exercise logs."""

    exercise_id = fields.Int(load_only=True)
    session_id = fields.Int(load_only=True, allow_none=True)
    planned_set_id = fields.Int(load_only=True, allow_none=True)
    performed_at = fields.DateTime(load_only=True)
    set_index = fields.Int(load_only=True)
    is_warmup = fields.Bool(load_only=True)
    to_failure = fields.Bool(load_only=True)
    actual_weight_kg = fields.Decimal(load_only=True, allow_none=True, as_string=True)
    actual_reps = fields.Int(load_only=True, allow_none=True)
    actual_rir = fields.Int(load_only=True, allow_none=True)
    actual_rpe = fields.Decimal(load_only=True, allow_none=True, as_string=True)
    actual_tempo = fields.String(load_only=True, allow_none=True)
    actual_rest_s = fields.Int(load_only=True, allow_none=True)
    notes = fields.String(load_only=True, allow_none=True)
