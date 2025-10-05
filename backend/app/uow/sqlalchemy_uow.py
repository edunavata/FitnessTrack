"""
SQLAlchemy implementation of UnitOfWork for Flask.
"""

from __future__ import annotations

from app.core.extensions import db
from app.repositories import (
    CycleRepository,
    ExerciseRepository,
    ExerciseSetLogRepository,
    RoutineRepository,
    SubjectBodyMetricsRepository,
    SubjectRepository,
    SubjectRoutineRepository,
    TagRepository,
    UserRepository,
    WorkoutSessionRepository,
)
from app.uow.base import UnitOfWork


class SQLAlchemyUnitOfWork(UnitOfWork):
    """
    SQLAlchemy-backed UoW using the Flask-scoped session.

    The same session is shared across all repositories for a consistent transaction.
    """

    def __init__(self) -> None:
        """Initialise the Unit of Work with a shared SQLAlchemy session.

        All repositories receive the same session instance so that they operate
        within the identical transactional context.
        """

        self.session = db.session

        # Repository instances share the same transactional session.
        self.users = UserRepository(session=self.session)
        self.subjects = SubjectRepository(session=self.session)
        self.subject_body_metrics = SubjectBodyMetricsRepository(session=self.session)
        self.exercises = ExerciseRepository(session=self.session)
        self.tags = TagRepository(session=self.session)
        self.routines = RoutineRepository(session=self.session)
        self.subject_routines = SubjectRoutineRepository(session=self.session)
        self.cycles = CycleRepository(session=self.session)
        self.workout_sessions = WorkoutSessionRepository(session=self.session)
        self.exercise_set_logs = ExerciseSetLogRepository(session=self.session)

    def __enter__(self) -> SQLAlchemyUnitOfWork:
        # No-op: the session is lazily started on the first write.
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
        else:
            self.rollback()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
