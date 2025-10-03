"""Idempotent database seed helpers for local development environments."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any, TypeVar, cast
from uuid import UUID

from app.models.cycle import Cycle
from app.models.exercise import (
    Exercise,
    ExerciseAlias,
    ExerciseTag,
    Tag,
)
from app.models.exercise_log import ExerciseSetLog
from app.models.exercise_secondary import ExerciseSecondaryMuscle
from app.models.routine import (
    Routine,
    RoutineDay,
    RoutineDayExercise,
    RoutineExerciseSet,
    SubjectRoutine,
)
from app.models.subject import SexEnum, Subject, SubjectBodyMetrics, SubjectProfile
from app.models.user import User
from app.models.workout import WorkoutSession
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from sqlalchemy.orm import Session

LOGGER = logging.getLogger(__name__)
UTC = UTC

T = TypeVar("T")

USER_FIXTURES: list[dict[str, str | None]] = [
    {
        "email": "alex.martinez@example.com",
        "username": "alexm",
        "full_name": "Alex Martinez",
        "password": "devPass123!",
    },
    {
        "email": "jamie.lee@example.com",
        "username": "jamielee",
        "full_name": "Jamie Lee",
        "password": "strongPass123",
    },
    {
        "email": "sara.kim@example.com",
        "username": "sarak",
        "full_name": "Sara Kim",
        "password": "liftMore2024",
    },
    {
        "email": "maria.garcia@example.com",
        "username": "mariag",
        "full_name": "Maria Garcia",
        "password": "wellness456",
    },
    {
        "email": "coach.dan@example.com",
        "username": "coachdan",
        "full_name": "Coach Dan",
        "password": "coachPower!",
    },
]

SUBJECT_FIXTURES: list[dict[str, Any]] = [
    {
        "key": "alex",
        "pseudonym": "b1c64957-4e1f-4d24-9abc-52c5c9982711",
        "user_email": "alex.martinez@example.com",
    },
    {
        "key": "jamie",
        "pseudonym": "6f7875bd-2511-4dc7-b0fc-45cbd90fb82d",
        "user_email": "jamie.lee@example.com",
    },
    {
        "key": "sara",
        "pseudonym": "5f8c8bdd-8ad4-4ca9-8cd4-8dbf65cb5dd2",
        "user_email": "sara.kim@example.com",
    },
    {
        "key": "maria",
        "pseudonym": "9d5b1c9e-55b9-4f4e-8e53-3d3551a8cbb4",
        "user_email": "maria.garcia@example.com",
    },
    {
        "key": "coach",
        "pseudonym": "3527d4f1-a548-4c18-9a2d-36cdb4be8f51",
        "user_email": "coach.dan@example.com",
    },
    {
        "key": "guest",
        "pseudonym": "d347f052-063b-4f81-86f2-e33c3ab84db9",
        "user_email": None,
    },
]

SUBJECT_PROFILE_FIXTURES: list[dict[str, Any]] = [
    {
        "subject_key": "alex",
        "sex": SexEnum.MALE,
        "birth_year": 1991,
        "height_cm": 178,
        "dominant_hand": "right",
    },
    {
        "subject_key": "jamie",
        "sex": SexEnum.FEMALE,
        "birth_year": 1990,
        "height_cm": 165,
        "dominant_hand": "left",
    },
    {
        "subject_key": "sara",
        "sex": SexEnum.FEMALE,
        "birth_year": 1987,
        "height_cm": 170,
        "dominant_hand": "right",
    },
    {
        "subject_key": "maria",
        "sex": SexEnum.FEMALE,
        "birth_year": 1995,
        "height_cm": 160,
        "dominant_hand": "right",
    },
    {
        "subject_key": "coach",
        "sex": SexEnum.MALE,
        "birth_year": 1980,
        "height_cm": 183,
        "dominant_hand": "right",
    },
]

BODY_METRICS_FIXTURES: list[dict[str, Any]] = [
    {
        "subject_key": "alex",
        "measured_on": date(2024, 3, 1),
        "weight_kg": 82.4,
        "bodyfat_pct": 15.2,
        "resting_hr": 58,
        "notes": "Start of spring mesocycle.",
    },
    {
        "subject_key": "alex",
        "measured_on": date(2024, 4, 1),
        "weight_kg": 81.6,
        "bodyfat_pct": 14.7,
        "resting_hr": 56,
        "notes": "Improved conditioning after first block.",
    },
    {
        "subject_key": "jamie",
        "measured_on": date(2024, 3, 5),
        "weight_kg": 64.2,
        "bodyfat_pct": 22.1,
        "resting_hr": 62,
        "notes": "Returning from off-season.",
    },
    {
        "subject_key": "sara",
        "measured_on": date(2024, 3, 10),
        "weight_kg": 58.7,
        "bodyfat_pct": 19.5,
        "resting_hr": 60,
        "notes": "Baseline check after deload week.",
    },
]

TAG_NAMES: list[str] = [
    "strength",
    "hypertrophy",
    "mobility",
    "conditioning",
    "powerlifting",
    "olympic",
]

EXERCISE_FIXTURES: list[dict[str, Any]] = [
    {
        "name": "Back Squat",
        "slug": "back-squat",
        "primary_muscle": "QUADS",
        "movement": "SQUAT",
        "mechanics": "COMPOUND",
        "force": "PUSH",
        "unilateral": False,
        "equipment": "BARBELL",
        "difficulty": "INTERMEDIATE",
        "aliases": ["Barbell Squat"],
        "secondary": ["GLUTES", "HAMSTRINGS"],
        "tags": ["strength", "powerlifting"],
        "instructions": "Set up with the barbell across the traps and squat below parallel while maintaining a neutral spine.",
    },
    {
        "name": "Bench Press",
        "slug": "bench-press",
        "primary_muscle": "CHEST",
        "movement": "HORIZONTAL_PUSH",
        "mechanics": "COMPOUND",
        "force": "PUSH",
        "unilateral": False,
        "equipment": "BARBELL",
        "difficulty": "INTERMEDIATE",
        "aliases": ["Flat Bench Press"],
        "secondary": ["TRICEPS", "SHOULDERS"],
        "tags": ["strength", "powerlifting"],
        "instructions": "Press the bar from the chest with controlled tempo and scapular retraction.",
    },
    {
        "name": "Overhead Press",
        "slug": "overhead-press",
        "primary_muscle": "SHOULDERS",
        "movement": "VERTICAL_PUSH",
        "mechanics": "COMPOUND",
        "force": "PUSH",
        "unilateral": False,
        "equipment": "BARBELL",
        "difficulty": "INTERMEDIATE",
        "aliases": ["Standing Press", "Military Press"],
        "secondary": ["TRICEPS"],
        "tags": ["strength"],
        "instructions": "Press the bar overhead while keeping ribs down and glutes tight.",
    },
    {
        "name": "Pendlay Row",
        "slug": "pendlay-row",
        "primary_muscle": "BACK",
        "movement": "HORIZONTAL_PULL",
        "mechanics": "COMPOUND",
        "force": "PULL",
        "unilateral": False,
        "equipment": "BARBELL",
        "difficulty": "INTERMEDIATE",
        "aliases": ["Barbell Row"],
        "secondary": ["BICEPS"],
        "tags": ["strength"],
        "instructions": "Pull explosively from the floor to the lower chest with a strict torso angle.",
    },
    {
        "name": "Lat Pulldown",
        "slug": "lat-pulldown",
        "primary_muscle": "BACK",
        "movement": "VERTICAL_PULL",
        "mechanics": "COMPOUND",
        "force": "PULL",
        "unilateral": False,
        "equipment": "MACHINE",
        "difficulty": "BEGINNER",
        "aliases": ["Cable Pulldown"],
        "secondary": ["BICEPS"],
        "tags": ["hypertrophy"],
        "instructions": "Pull the bar towards the chest while keeping the torso tall and shoulder blades depressed.",
    },
    {
        "name": "Romanian Deadlift",
        "slug": "romanian-deadlift",
        "primary_muscle": "HAMSTRINGS",
        "movement": "HINGE",
        "mechanics": "COMPOUND",
        "force": "PULL",
        "unilateral": False,
        "equipment": "BARBELL",
        "difficulty": "INTERMEDIATE",
        "aliases": ["RDL"],
        "secondary": ["GLUTES", "BACK"],
        "tags": ["strength", "hypertrophy"],
        "instructions": "Hinge at the hips keeping a slight knee bend and maintain tension through the posterior chain.",
    },
    {
        "name": "Walking Lunge",
        "slug": "walking-lunge",
        "primary_muscle": "GLUTES",
        "movement": "LUNGE",
        "mechanics": "COMPOUND",
        "force": "PUSH",
        "unilateral": True,
        "equipment": "DUMBBELL",
        "difficulty": "BEGINNER",
        "aliases": ["Dumbbell Lunge"],
        "secondary": ["QUADS", "HAMSTRINGS"],
        "tags": ["hypertrophy", "conditioning"],
        "instructions": "Step forward under control, descend until the back knee hovers above the floor, and drive through the front heel.",
    },
    {
        "name": "Face Pull",
        "slug": "face-pull",
        "primary_muscle": "SHOULDERS",
        "movement": "HORIZONTAL_PULL",
        "mechanics": "ISOLATION",
        "force": "PULL",
        "unilateral": False,
        "equipment": "CABLE",
        "difficulty": "BEGINNER",
        "aliases": ["Rope Face Pull"],
        "secondary": ["BACK"],
        "tags": ["mobility", "hypertrophy"],
        "instructions": "Pull the rope towards the face keeping elbows high to target the rear delts.",
    },
    {
        "name": "Dead Bug",
        "slug": "dead-bug",
        "primary_muscle": "ABS",
        "movement": "CORE_BRACE",
        "mechanics": "ISOLATION",
        "force": "STATIC",
        "unilateral": False,
        "equipment": "BODYWEIGHT",
        "difficulty": "BEGINNER",
        "aliases": ["Core Dead Bug"],
        "secondary": ["HIP_FLEXORS"],
        "tags": ["mobility"],
        "instructions": "Maintain spinal contact with the floor while alternating contralateral limbs.",
    },
    {
        "name": "Kettlebell Swing",
        "slug": "kettlebell-swing",
        "primary_muscle": "GLUTES",
        "movement": "HINGE",
        "mechanics": "COMPOUND",
        "force": "PULL",
        "unilateral": False,
        "equipment": "KETTLEBELL",
        "difficulty": "INTERMEDIATE",
        "aliases": ["KB Swing"],
        "secondary": ["HAMSTRINGS", "BACK"],
        "tags": ["conditioning", "olympic"],
        "instructions": "Drive the bell explosively with hip extension while keeping the lats engaged.",
    },
]

ROUTINE_FIXTURES: list[dict[str, Any]] = [
    {
        "key": "ppl_intro",
        "name": "Hypertrophy Push/Pull/Legs",
        "owner_subject_key": "alex",
        "description": "Three-day split focused on compound lifts with accessory volume.",
        "is_public": True,
        "shared_with": ["jamie", "sara"],
        "days": [
            {
                "day_index": 1,
                "title": "Push Day",
                "notes": "Emphasis on horizontal and vertical pressing.",
                "exercises": [
                    {
                        "slug": "bench-press",
                        "position": 1,
                        "notes": "Competition grip.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 82.5,
                                "target_reps": 6,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 82.5,
                                "target_reps": 6,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                            {
                                "set_index": 3,
                                "target_weight_kg": 77.5,
                                "target_reps": 8,
                                "target_rir": 1,
                                "target_rest_s": 120,
                            },
                        ],
                    },
                    {
                        "slug": "overhead-press",
                        "position": 2,
                        "notes": None,
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 52.5,
                                "target_reps": 8,
                                "target_rir": 2,
                                "target_rest_s": 120,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 50.0,
                                "target_reps": 10,
                                "target_rir": 1,
                                "target_rest_s": 120,
                            },
                        ],
                    },
                    {
                        "slug": "face-pull",
                        "position": 3,
                        "notes": "Focus on scapular control.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 25.0,
                                "target_reps": 15,
                                "target_rir": 1,
                                "target_rest_s": 60,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 25.0,
                                "target_reps": 15,
                                "target_rir": 1,
                                "target_rest_s": 60,
                            },
                        ],
                    },
                ],
            },
            {
                "day_index": 2,
                "title": "Pull Day",
                "notes": "Posterior chain and lat focus.",
                "exercises": [
                    {
                        "slug": "pendlay-row",
                        "position": 1,
                        "notes": None,
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 90.0,
                                "target_reps": 6,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 90.0,
                                "target_reps": 6,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                        ],
                    },
                    {
                        "slug": "lat-pulldown",
                        "position": 2,
                        "notes": "Pause at bottom.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 60.0,
                                "target_reps": 12,
                                "target_rir": 2,
                                "target_rest_s": 90,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 55.0,
                                "target_reps": 15,
                                "target_rir": 1,
                                "target_rest_s": 90,
                            },
                        ],
                    },
                    {
                        "slug": "dead-bug",
                        "position": 3,
                        "notes": "Controlled tempo.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_reps": 12,
                                "target_rir": 1,
                                "target_rest_s": 45,
                            },
                            {
                                "set_index": 2,
                                "target_reps": 12,
                                "target_rir": 1,
                                "target_rest_s": 45,
                            },
                        ],
                    },
                ],
            },
            {
                "day_index": 3,
                "title": "Leg Day",
                "notes": "Heavy squat plus hinge accessory.",
                "exercises": [
                    {
                        "slug": "back-squat",
                        "position": 1,
                        "notes": None,
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 140.0,
                                "target_reps": 5,
                                "target_rir": 1,
                                "target_rest_s": 180,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 130.0,
                                "target_reps": 6,
                                "target_rir": 2,
                                "target_rest_s": 180,
                            },
                        ],
                    },
                    {
                        "slug": "romanian-deadlift",
                        "position": 2,
                        "notes": "Keep lats packed.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 110.0,
                                "target_reps": 8,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 105.0,
                                "target_reps": 10,
                                "target_rir": 1,
                                "target_rest_s": 150,
                            },
                        ],
                    },
                    {
                        "slug": "walking-lunge",
                        "position": 3,
                        "notes": "Steps per leg.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_reps": 12,
                                "target_rir": 2,
                                "target_rest_s": 90,
                            },
                            {
                                "set_index": 2,
                                "target_reps": 12,
                                "target_rir": 2,
                                "target_rest_s": 90,
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "key": "minimal_full_body",
        "name": "Minimalist Full Body",
        "owner_subject_key": "jamie",
        "description": "Two day template alternating full-body sessions for busy weeks.",
        "is_public": False,
        "shared_with": ["maria"],
        "days": [
            {
                "day_index": 1,
                "title": "Session A",
                "notes": "Strength focus with kettlebell conditioning finisher.",
                "exercises": [
                    {
                        "slug": "back-squat",
                        "position": 1,
                        "notes": "Technique emphasis.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 85.0,
                                "target_reps": 5,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                            {
                                "set_index": 2,
                                "target_weight_kg": 90.0,
                                "target_reps": 5,
                                "target_rir": 2,
                                "target_rest_s": 150,
                            },
                        ],
                    },
                    {
                        "slug": "bench-press",
                        "position": 2,
                        "notes": None,
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 60.0,
                                "target_reps": 8,
                                "target_rir": 1,
                                "target_rest_s": 120,
                            },
                        ],
                    },
                    {
                        "slug": "kettlebell-swing",
                        "position": 3,
                        "notes": "EMOM finisher.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_reps": 15,
                                "target_rir": 2,
                                "target_rest_s": 60,
                            },
                        ],
                    },
                ],
            },
            {
                "day_index": 2,
                "title": "Session B",
                "notes": "Posterior chain and core.",
                "exercises": [
                    {
                        "slug": "romanian-deadlift",
                        "position": 1,
                        "notes": None,
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 75.0,
                                "target_reps": 8,
                                "target_rir": 2,
                                "target_rest_s": 120,
                            },
                        ],
                    },
                    {
                        "slug": "lat-pulldown",
                        "position": 2,
                        "notes": "Neutral grip handle.",
                        "sets": [
                            {
                                "set_index": 1,
                                "target_weight_kg": 45.0,
                                "target_reps": 12,
                                "target_rir": 2,
                                "target_rest_s": 90,
                            },
                        ],
                    },
                    {
                        "slug": "dead-bug",
                        "position": 3,
                        "notes": None,
                        "sets": [
                            {
                                "set_index": 1,
                                "target_reps": 10,
                                "target_rir": 2,
                                "target_rest_s": 45,
                            },
                        ],
                    },
                ],
            },
        ],
    },
]

CYCLE_FIXTURES: list[dict[str, Any]] = [
    {
        "subject_key": "alex",
        "routine_key": "ppl_intro",
        "cycle_number": 1,
        "started_on": date(2024, 3, 18),
        "ended_on": None,
        "notes": "Spring hypertrophy block.",
    },
    {
        "subject_key": "jamie",
        "routine_key": "minimal_full_body",
        "cycle_number": 1,
        "started_on": date(2024, 3, 12),
        "ended_on": None,
        "notes": "Time-constrained cycle leading into competition prep.",
    },
]

WORKOUT_FIXTURES: list[dict[str, Any]] = [
    {
        "subject_key": "alex",
        "routine_key": "ppl_intro",
        "workout_date": datetime(2024, 3, 18, 17, 30, tzinfo=UTC),
        "status": "COMPLETED",
        "routine_day_index": 1,
        "cycle_number": 1,
        "location": "Garage Gym",
        "perceived_fatigue": 3,
        "bodyweight_kg": 82.2,
        "notes": "Strong pressing session.",
    },
    {
        "subject_key": "alex",
        "routine_key": "ppl_intro",
        "workout_date": datetime(2024, 3, 20, 18, 0, tzinfo=UTC),
        "status": "COMPLETED",
        "routine_day_index": 2,
        "cycle_number": 1,
        "location": "Garage Gym",
        "perceived_fatigue": 4,
        "bodyweight_kg": 82.0,
        "notes": "Back pumps and solid tempo work.",
    },
    {
        "subject_key": "jamie",
        "routine_key": "minimal_full_body",
        "workout_date": datetime(2024, 3, 13, 12, 15, tzinfo=UTC),
        "status": "COMPLETED",
        "routine_day_index": 1,
        "cycle_number": 1,
        "location": "Community Gym",
        "perceived_fatigue": 2,
        "bodyweight_kg": 64.1,
        "notes": "Quick lunch session.",
    },
]

EXERCISE_LOG_FIXTURES: list[dict[str, Any]] = [
    {
        "subject_key": "alex",
        "exercise_slug": "bench-press",
        "performed_at": datetime(2024, 3, 18, 17, 45, tzinfo=UTC),
        "set_index": 1,
        "actual_weight_kg": 82.5,
        "actual_reps": 6,
        "actual_rir": 2,
        "actual_rest_s": 150,
        "session_key": ("alex", datetime(2024, 3, 18, 17, 30, tzinfo=UTC)),
        "planned_set": {
            "routine_key": "ppl_intro",
            "routine_day_index": 1,
            "exercise_slug": "bench-press",
            "set_index": 1,
        },
    },
    {
        "subject_key": "alex",
        "exercise_slug": "bench-press",
        "performed_at": datetime(2024, 3, 18, 17, 52, tzinfo=UTC),
        "set_index": 2,
        "actual_weight_kg": 82.5,
        "actual_reps": 6,
        "actual_rir": 2,
        "actual_rest_s": 150,
        "session_key": ("alex", datetime(2024, 3, 18, 17, 30, tzinfo=UTC)),
        "planned_set": {
            "routine_key": "ppl_intro",
            "routine_day_index": 1,
            "exercise_slug": "bench-press",
            "set_index": 2,
        },
    },
    {
        "subject_key": "alex",
        "exercise_slug": "bench-press",
        "performed_at": datetime(2024, 3, 18, 18, 1, tzinfo=UTC),
        "set_index": 3,
        "actual_weight_kg": 77.5,
        "actual_reps": 8,
        "actual_rir": 1,
        "actual_rest_s": 120,
        "session_key": ("alex", datetime(2024, 3, 18, 17, 30, tzinfo=UTC)),
        "planned_set": {
            "routine_key": "ppl_intro",
            "routine_day_index": 1,
            "exercise_slug": "bench-press",
            "set_index": 3,
        },
    },
    {
        "subject_key": "alex",
        "exercise_slug": "pendlay-row",
        "performed_at": datetime(2024, 3, 20, 18, 15, tzinfo=UTC),
        "set_index": 1,
        "actual_weight_kg": 90.0,
        "actual_reps": 6,
        "actual_rir": 2,
        "actual_rest_s": 150,
        "session_key": ("alex", datetime(2024, 3, 20, 18, 0, tzinfo=UTC)),
        "planned_set": {
            "routine_key": "ppl_intro",
            "routine_day_index": 2,
            "exercise_slug": "pendlay-row",
            "set_index": 1,
        },
    },
    {
        "subject_key": "jamie",
        "exercise_slug": "kettlebell-swing",
        "performed_at": datetime(2024, 3, 13, 12, 32, tzinfo=UTC),
        "set_index": 1,
        "actual_reps": 15,
        "actual_rir": 2,
        "actual_rest_s": 60,
        "session_key": ("jamie", datetime(2024, 3, 13, 12, 15, tzinfo=UTC)),
        "planned_set": {
            "routine_key": "minimal_full_body",
            "routine_day_index": 1,
            "exercise_slug": "kettlebell-swing",
            "set_index": 1,
        },
    },
]


def _session(database: SQLAlchemy) -> Session:
    """Return the current SQLAlchemy session."""
    return cast(Session, database.session)


def _touch(summary: dict[str, dict[str, int]], table: str, created: bool) -> None:
    """Update summary counters for the given table."""
    entry = summary.setdefault(table, {"created": 0, "existing": 0})
    if created:
        entry["created"] += 1
    else:
        entry["existing"] += 1


def _get_or_create(
    session: Session,
    model: type[T],
    *,
    defaults: dict[str, Any] | None = None,
    **filters: Any,
) -> tuple[T, bool]:
    """Fetch ``model`` by ``filters`` or create it using ``defaults``."""
    instance = session.execute(select(model).filter_by(**filters)).scalar_one_or_none()
    if instance is not None:
        return instance, False
    params = dict(defaults or {})
    params.update(filters)
    instance = cast(T, model(**params))
    session.add(instance)
    return instance, True


def seed_users_and_subjects(
    database: SQLAlchemy, *, verbose: bool = False
) -> dict[str, dict[str, int]]:
    """Create core authentication users, subjects, and subject metrics."""
    if verbose:
        LOGGER.info("Seeding users and subjects...")
    session = _session(database)
    summary: dict[str, dict[str, int]] = {}
    email_to_user: dict[str, User] = {}
    subject_lookup: dict[str, Subject] = {}

    with session.begin():
        for fixture in USER_FIXTURES:
            email = str(fixture["email"]).strip().lower()
            user = session.execute(select(User).filter_by(email=email)).scalar_one_or_none()
            created = False
            if user is None:
                user = User(
                    email=email,
                    username=str(fixture["username"]),
                    full_name=fixture.get("full_name"),
                )
                password = fixture.get("password")
                if isinstance(password, str) and password:
                    user.password = password
                session.add(user)
                created = True
            else:
                user.username = str(fixture["username"])
                user.full_name = fixture.get("full_name")
            session.flush()
            email_to_user[email] = user
            _touch(summary, "users", created)

        for fixture in SUBJECT_FIXTURES:
            subject_key_value = fixture.get("key")
            if not isinstance(subject_key_value, str):
                raise RuntimeError("Subject fixture missing key identifier")
            pseudonym = UUID(str(fixture["pseudonym"]))
            subject = session.execute(
                select(Subject).filter_by(pseudonym=pseudonym)
            ).scalar_one_or_none()
            created = False
            user_email = fixture.get("user_email")
            user = email_to_user.get(str(user_email).strip().lower()) if user_email else None
            if subject is None:
                subject = Subject(pseudonym=pseudonym)
                if user is not None:
                    subject.user_id = user.id
                session.add(subject)
                created = True
            else:
                subject.user_id = user.id if user is not None else None
            session.flush()
            subject_lookup[subject_key_value] = subject
            _touch(summary, "subjects", created)

        for profile in SUBJECT_PROFILE_FIXTURES:
            subject_key_value = profile.get("subject_key")
            if not isinstance(subject_key_value, str):
                raise RuntimeError("Subject key missing while creating profile")
            subject_key = subject_key_value
            subject = subject_lookup.get(subject_key)
            if subject is None:
                raise RuntimeError(f"Subject {subject_key} missing while creating profile")
            profile_instance = session.execute(
                select(SubjectProfile).filter_by(subject_id=subject.id)
            ).scalar_one_or_none()
            created = False
            if profile_instance is None:
                profile_instance = SubjectProfile(subject_id=subject.id)
                session.add(profile_instance)
                created = True
            profile_instance.sex = profile.get("sex")
            profile_instance.birth_year = profile.get("birth_year")
            profile_instance.height_cm = profile.get("height_cm")
            profile_instance.dominant_hand = profile.get("dominant_hand")
            session.flush()
            _touch(summary, "subject_profiles", created)

        for metrics in BODY_METRICS_FIXTURES:
            subject_key_value = metrics.get("subject_key")
            if not isinstance(subject_key_value, str):
                raise RuntimeError("Subject key missing while creating body metrics")
            subject_key = subject_key_value
            subject = subject_lookup.get(subject_key)
            if subject is None:
                raise RuntimeError(f"Subject {subject_key} missing while creating body metrics")
            metrics_instance, created = _get_or_create(
                session,
                SubjectBodyMetrics,
                subject_id=subject.id,
                measured_on=metrics["measured_on"],
            )
            metrics_instance.weight_kg = metrics.get("weight_kg")
            metrics_instance.bodyfat_pct = metrics.get("bodyfat_pct")
            metrics_instance.resting_hr = metrics.get("resting_hr")
            metrics_instance.notes = metrics.get("notes")
            session.flush()
            _touch(summary, "subject_body_metrics", created)

    return summary


def seed_core_taxonomies(
    database: SQLAlchemy, *, verbose: bool = False
) -> dict[str, dict[str, int]]:
    """Populate exercise catalogs, tags, and associations."""
    if verbose:
        LOGGER.info("Seeding exercise catalog and tags...")
    session = _session(database)
    summary: dict[str, dict[str, int]] = {}

    with session.begin():
        tag_lookup: dict[str, Tag] = {}
        for name in TAG_NAMES:
            tag_instance, created = _get_or_create(session, Tag, name=name)
            tag_lookup[name] = tag_instance
            _touch(summary, "tags", created)

        for exercise_data in EXERCISE_FIXTURES:
            slug = exercise_data["slug"]
            defaults = {
                key: exercise_data.get(key)
                for key in (
                    "name",
                    "primary_muscle",
                    "movement",
                    "mechanics",
                    "force",
                    "unilateral",
                    "equipment",
                    "grip",
                    "range_of_motion",
                    "difficulty",
                    "cues",
                    "instructions",
                    "video_url",
                    "is_active",
                )
                if exercise_data.get(key) is not None
            }
            exercise, created = _get_or_create(session, Exercise, slug=slug, defaults=defaults)
            if not created:
                for attr, value in defaults.items():
                    setattr(exercise, attr, value)
            session.flush()
            _touch(summary, "exercises", created)

            for alias in exercise_data.get("aliases", []):
                _, alias_created = _get_or_create(
                    session,
                    ExerciseAlias,
                    exercise_id=exercise.id,
                    alias=alias,
                )
                _touch(summary, "exercise_aliases", alias_created)

            for muscle in exercise_data.get("secondary", []):
                _, secondary_created = _get_or_create(
                    session,
                    ExerciseSecondaryMuscle,
                    exercise_id=exercise.id,
                    muscle=muscle,
                )
                _touch(summary, "exercise_secondary_muscles", secondary_created)

            for tag_name in exercise_data.get("tags", []):
                tag_record = tag_lookup.get(tag_name)
                if tag_record is None:
                    continue
                _, link_created = _get_or_create(
                    session,
                    ExerciseTag,
                    exercise_id=exercise.id,
                    tag_id=tag_record.id,
                )
                _touch(summary, "exercise_tags", link_created)

    return summary


def seed_routines_cycles_workouts(
    database: SQLAlchemy,
    *,
    verbose: bool = False,
) -> dict[str, dict[str, int]]:
    """Create routines, subject associations, cycles, workouts, and logs."""
    if verbose:
        LOGGER.info("Seeding routines, cycles, workouts, and logs...")
    session = _session(database)
    summary: dict[str, dict[str, int]] = {}

    with session.begin():
        subject_lookup: dict[str, Subject] = {}
        for fixture in SUBJECT_FIXTURES:
            subject_key_value = fixture.get("key")
            if not isinstance(subject_key_value, str):
                raise RuntimeError("Subject fixture missing key identifier")
            pseudonym = UUID(str(fixture["pseudonym"]))
            subject = session.execute(
                select(Subject).filter_by(pseudonym=pseudonym)
            ).scalar_one_or_none()
            if subject is not None:
                subject_lookup[subject_key_value] = subject
        missing = [
            key
            for fixture in SUBJECT_FIXTURES
            for key in [fixture.get("key")]
            if isinstance(key, str) and key not in subject_lookup
        ]
        if missing:
            raise RuntimeError(f"Subjects missing before routine seeding: {missing}")

        slugs = {exercise["slug"] for exercise in EXERCISE_FIXTURES}
        exercise_lookup: dict[str, Exercise] = {
            slug: session.execute(select(Exercise).filter_by(slug=slug)).scalar_one()
            for slug in slugs
        }

        routine_lookup: dict[str, Routine] = {}
        routine_day_lookup: dict[tuple[str, int], RoutineDay] = {}
        routine_set_lookup: dict[tuple[str, int, str, int], RoutineExerciseSet] = {}

        for routine_data in ROUTINE_FIXTURES:
            owner = subject_lookup[routine_data["owner_subject_key"]]
            routine = session.execute(
                select(Routine).filter_by(owner_subject_id=owner.id, name=routine_data["name"])
            ).scalar_one_or_none()
            created = False
            if routine is None:
                routine = Routine(
                    owner_subject_id=owner.id,
                    name=routine_data["name"],
                )
                session.add(routine)
                created = True
            routine.description = routine_data.get("description")
            routine.is_public = bool(routine_data.get("is_public", False))
            session.flush()
            routine_lookup[routine_data["key"]] = routine
            _touch(summary, "routines", created)

            for day in routine_data.get("days", []):
                routine_day = session.execute(
                    select(RoutineDay).filter_by(
                        routine_id=routine.id,
                        day_index=day["day_index"],
                    )
                ).scalar_one_or_none()
                day_created = False
                if routine_day is None:
                    routine_day = RoutineDay(
                        routine_id=routine.id,
                        day_index=day["day_index"],
                    )
                    session.add(routine_day)
                    day_created = True
                routine_day.title = day.get("title")
                routine_day.is_rest = bool(day.get("is_rest", False))
                routine_day.notes = day.get("notes")
                session.flush()
                routine_day_lookup[(routine_data["key"], day["day_index"])] = routine_day
                _touch(summary, "routine_days", day_created)

                for exercise_entry in day.get("exercises", []):
                    exercise = exercise_lookup[exercise_entry["slug"]]
                    day_exercise = session.execute(
                        select(RoutineDayExercise).filter_by(
                            routine_day_id=routine_day.id,
                            position=exercise_entry["position"],
                        )
                    ).scalar_one_or_none()
                    day_ex_created = False
                    if day_exercise is None:
                        day_exercise = RoutineDayExercise(
                            routine_day_id=routine_day.id,
                            position=exercise_entry["position"],
                        )
                        session.add(day_exercise)
                        day_ex_created = True
                    day_exercise.exercise_id = exercise.id
                    day_exercise.notes = exercise_entry.get("notes")
                    session.flush()
                    _touch(summary, "routine_day_exercises", day_ex_created)

                    for set_entry in exercise_entry.get("sets", []):
                        routine_set = session.execute(
                            select(RoutineExerciseSet).filter_by(
                                routine_day_exercise_id=day_exercise.id,
                                set_index=set_entry["set_index"],
                            )
                        ).scalar_one_or_none()
                        set_created = False
                        if routine_set is None:
                            routine_set = RoutineExerciseSet(
                                routine_day_exercise_id=day_exercise.id,
                                set_index=set_entry["set_index"],
                            )
                            session.add(routine_set)
                            set_created = True
                        routine_set.is_warmup = bool(set_entry.get("is_warmup", False))
                        routine_set.to_failure = bool(set_entry.get("to_failure", False))
                        routine_set.target_weight_kg = set_entry.get("target_weight_kg")
                        routine_set.target_reps = set_entry.get("target_reps")
                        routine_set.target_rir = set_entry.get("target_rir")
                        routine_set.target_rpe = set_entry.get("target_rpe")
                        routine_set.target_tempo = set_entry.get("target_tempo")
                        routine_set.target_rest_s = set_entry.get("target_rest_s")
                        routine_set.notes = set_entry.get("notes")
                        session.flush()
                        routine_set_lookup[
                            (
                                routine_data["key"],
                                day["day_index"],
                                exercise_entry["slug"],
                                set_entry["set_index"],
                            )
                        ] = routine_set
                        _touch(summary, "routine_exercise_sets", set_created)

            for subject_key in routine_data.get("shared_with", []):
                subject = subject_lookup[subject_key]
                association, created_assoc = _get_or_create(
                    session,
                    SubjectRoutine,
                    subject_id=subject.id,
                    routine_id=routine.id,
                )
                association.is_active = True
                _touch(summary, "subject_routines", created_assoc)

        cycle_lookup: dict[tuple[str, str, int], Cycle] = {}
        for cycle_data in CYCLE_FIXTURES:
            subject = subject_lookup[cycle_data["subject_key"]]
            routine = routine_lookup[cycle_data["routine_key"]]
            cycle = session.execute(
                select(Cycle).filter_by(
                    subject_id=subject.id,
                    routine_id=routine.id,
                    cycle_number=cycle_data["cycle_number"],
                )
            ).scalar_one_or_none()
            created = False
            if cycle is None:
                cycle = Cycle(
                    subject_id=subject.id,
                    routine_id=routine.id,
                    cycle_number=cycle_data["cycle_number"],
                )
                session.add(cycle)
                created = True
            cycle.started_on = cycle_data.get("started_on")
            cycle.ended_on = cycle_data.get("ended_on")
            cycle.notes = cycle_data.get("notes")
            session.flush()
            cycle_lookup[
                (cycle_data["subject_key"], cycle_data["routine_key"], cycle_data["cycle_number"])
            ] = cycle
            _touch(summary, "cycles", created)

        session_lookup: dict[tuple[str, datetime], WorkoutSession] = {}
        for workout_data in WORKOUT_FIXTURES:
            subject = subject_lookup[workout_data["subject_key"]]
            routine_day_index = workout_data.get("routine_day_index")
            routine_day = (
                routine_day_lookup.get((workout_data["routine_key"], routine_day_index))
                if routine_day_index is not None
                else None
            )
            cycle = cycle_lookup.get(
                (
                    workout_data["subject_key"],
                    workout_data["routine_key"],
                    workout_data.get("cycle_number", 1),
                )
            )
            workout = session.execute(
                select(WorkoutSession).filter_by(
                    subject_id=subject.id,
                    workout_date=workout_data["workout_date"],
                )
            ).scalar_one_or_none()
            created = False
            if workout is None:
                workout = WorkoutSession(
                    subject_id=subject.id,
                    workout_date=workout_data["workout_date"],
                )
                session.add(workout)
                created = True
            workout.status = workout_data.get("status", "COMPLETED")
            workout.routine_day_id = routine_day.id if routine_day is not None else None
            workout.cycle_id = cycle.id if cycle is not None else None
            workout.location = workout_data.get("location")
            workout.perceived_fatigue = workout_data.get("perceived_fatigue")
            workout.bodyweight_kg = workout_data.get("bodyweight_kg")
            workout.notes = workout_data.get("notes")
            session.flush()
            session_lookup[(workout_data["subject_key"], workout_data["workout_date"])] = workout
            _touch(summary, "workout_sessions", created)

        for log_data in EXERCISE_LOG_FIXTURES:
            subject = subject_lookup[log_data["subject_key"]]
            exercise = exercise_lookup[log_data["exercise_slug"]]
            log = session.execute(
                select(ExerciseSetLog).filter_by(
                    subject_id=subject.id,
                    exercise_id=exercise.id,
                    performed_at=log_data["performed_at"],
                    set_index=log_data["set_index"],
                )
            ).scalar_one_or_none()
            created = False
            if log is None:
                log = ExerciseSetLog(
                    subject_id=subject.id,
                    exercise_id=exercise.id,
                    performed_at=log_data["performed_at"],
                    set_index=log_data["set_index"],
                )
                session.add(log)
                created = True
            session_key = log_data.get("session_key")
            if (
                isinstance(session_key, tuple)
                and len(session_key) == 2
                and isinstance(session_key[0], str)
                and isinstance(session_key[1], datetime)
            ):
                workout = session_lookup.get((session_key[0], session_key[1]))
                log.session_id = workout.id if workout is not None else None
            planned = log_data.get("planned_set")
            if isinstance(planned, dict):
                routine_key = planned.get("routine_key")
                day_index = planned.get("routine_day_index")
                exercise_slug = planned.get("exercise_slug")
                set_index = planned.get("set_index")
                if (
                    isinstance(routine_key, str)
                    and isinstance(day_index, int)
                    and isinstance(exercise_slug, str)
                    and isinstance(set_index, int)
                ):
                    planned_set = routine_set_lookup.get(
                        (routine_key, day_index, exercise_slug, set_index)
                    )
                    log.planned_set_id = planned_set.id if planned_set is not None else None
            log.actual_weight_kg = log_data.get("actual_weight_kg")
            log.actual_reps = log_data.get("actual_reps")
            log.actual_rir = log_data.get("actual_rir")
            log.actual_rpe = log_data.get("actual_rpe")
            log.actual_tempo = log_data.get("actual_tempo")
            log.actual_rest_s = log_data.get("actual_rest_s")
            log.is_warmup = bool(log_data.get("is_warmup", False))
            log.to_failure = bool(log_data.get("to_failure", False))
            log.notes = log_data.get("notes")
            session.flush()
            _touch(summary, "exercise_set_logs", created)

    return summary


def run_all(database: SQLAlchemy, *, verbose: bool = False) -> dict[str, dict[str, int]]:
    """Run all seeders in the correct foreign-key order."""
    if verbose:
        LOGGER.info("Running full seed pipeline...")
    combined: dict[str, dict[str, int]] = {}
    for func in (
        seed_users_and_subjects,
        seed_core_taxonomies,
        seed_routines_cycles_workouts,
    ):
        result = func(database, verbose=verbose)
        for table, counters in result.items():
            entry = combined.setdefault(table, {"created": 0, "existing": 0})
            entry["created"] += counters.get("created", 0)
            entry["existing"] += counters.get("existing", 0)
    return combined


__all__ = [
    "seed_core_taxonomies",
    "seed_users_and_subjects",
    "seed_routines_cycles_workouts",
    "run_all",
]


if __name__ == "__main__":  # pragma: no cover - developer convenience
    print("Seed module loaded. Use 'flask seed run' within an application context.")
