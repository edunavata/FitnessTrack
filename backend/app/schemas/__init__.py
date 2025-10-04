"""Convenience exports for application schemas."""

from __future__ import annotations

from .auth import LoginSchema, RegisterSchema, TokenResponseSchema, WhoAmISchema
from .common import MetaSchema, PaginationQuerySchema, SortQuerySchema, build_meta
from .exercise import ExerciseCreateSchema, ExerciseSchema
from .routine import RoutineCreateSchema, RoutineSchema
from .subject import SubjectCreateSchema, SubjectSchema
from .user import UserCreateSchema, UserSchema
from .workout import WorkoutCreateSchema, WorkoutSchema

__all__ = [
    "LoginSchema",
    "RegisterSchema",
    "TokenResponseSchema",
    "WhoAmISchema",
    "PaginationQuerySchema",
    "SortQuerySchema",
    "MetaSchema",
    "build_meta",
    "ExerciseSchema",
    "ExerciseCreateSchema",
    "RoutineSchema",
    "RoutineCreateSchema",
    "SubjectSchema",
    "SubjectCreateSchema",
    "UserSchema",
    "UserCreateSchema",
    "WorkoutSchema",
    "WorkoutCreateSchema",
]
