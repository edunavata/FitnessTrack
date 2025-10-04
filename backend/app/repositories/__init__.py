"""Repository package exposing persistence-layer access for all domain models."""

from __future__ import annotations

# ---------------------------------------------------------------------
# Core base exports (solo imports arriba; nada de asignaciones aún)
# ---------------------------------------------------------------------
from app.repositories import base as base_module
from app.repositories.base import (
    BaseRepository,
    Page,
    Pagination,
    paginate_select,
)

# ---------------------------------------------------------------------
# Domain-specific repositories (todos los imports seguidos)
# ---------------------------------------------------------------------
from app.repositories.cycle import CycleRepository
from app.repositories.exercise import ExerciseRepository
from app.repositories.exercise_set_log import ExerciseSetLogRepository
from app.repositories.routine import RoutineRepository, SubjectRoutineRepository
from app.repositories.subject import SubjectRepository
from app.repositories.subject_body_metrics import SubjectBodyMetricsRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.repositories.workout import WorkoutSessionRepository

# ---------------------------------------------------------------------
# Asignaciones y API pública (después de TODOS los imports)
# ---------------------------------------------------------------------

# Re-export público esperado por tests/otros módulos
apply_sorting = base_module._apply_sorting

__all__ = [
    # Base
    "BaseRepository",
    "Page",
    "Pagination",
    "paginate_select",
    "apply_sorting",
    # Domain
    "SubjectRepository",
    "SubjectBodyMetricsRepository",
    "ExerciseRepository",
    "TagRepository",
    "UserRepository",
    "RoutineRepository",
    "SubjectRoutineRepository",
    "CycleRepository",
    "WorkoutSessionRepository",
    "ExerciseSetLogRepository",
]
