"""
SQLAlchemy implementation of UnitOfWork for Flask.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

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

# --------------------------------------------------------------------------- #
# Supported isolation levels (cross-dialect reference)
# --------------------------------------------------------------------------- #

VALID_ISOLATION_LEVELS_BY_DIALECT = {
    "postgresql": {"READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"},
    "mysql": {"READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"},
    "sqlite": {"AUTOCOMMIT", "SERIALIZABLE"},
}


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


# --------------------------------------------------------------------------- #
# Read-only UoW
# --------------------------------------------------------------------------- #

# -------------------------- Read-only strategy API -------------------------- #


class ReadOnlyStrategy(Protocol):
    """
    Strategy for applying database-level READ ONLY semantics.

    The strategy decides if and how to enable transaction-level READ ONLY for a
    given dialect, and at which phase (pre- or post- BEGIN).
    """

    def pre_begin(self, conn: Connection) -> None:
        """Hook executed before the ORM transaction starts."""
        ...

    def post_begin(self, session) -> None:
        """Hook executed after the ORM transaction starts."""
        ...


class NoopReadOnlyStrategy:
    """Fallback strategy for dialects without transaction-level READ ONLY."""

    def pre_begin(self, conn: Connection) -> None:
        return

    def post_begin(self, session) -> None:
        return


class PostgresReadOnlyStrategy:
    """PostgreSQL requires SET TRANSACTION READ ONLY *after* BEGIN."""

    def pre_begin(self, conn: Connection) -> None:
        return

    def post_begin(self, session) -> None:
        session.execute(text("SET TRANSACTION READ ONLY"))


class MySQLReadOnlyStrategy:
    """MySQL/MariaDB apply SET TRANSACTION READ ONLY *before* the next BEGIN."""

    def pre_begin(self, conn: Connection) -> None:
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")

    def post_begin(self, session) -> None:
        return


def select_readonly_strategy(dialect_name: str | None, enabled: bool) -> ReadOnlyStrategy:
    """
    Choose an appropriate READ ONLY strategy based on dialect.

    Parameters
    ----------
    dialect_name:
        SQLAlchemy dialect name (e.g. "postgresql", "mysql", "sqlite").
    enabled:
        Whether DB-level READ ONLY enforcement is requested.

    Returns
    -------
    ReadOnlyStrategy
        Strategy instance to use for the current transaction.
    """
    if not enabled or not dialect_name:
        return NoopReadOnlyStrategy()
    if dialect_name == "postgresql":
        return PostgresReadOnlyStrategy()
    if dialect_name in {"mysql", "mariadb"}:
        return MySQLReadOnlyStrategy()
    # SQLite / others: no portable per-transaction READ ONLY
    return NoopReadOnlyStrategy()


# --------------------------- Read-only UoW class --------------------------- #


class ReadOnlyViolation(RuntimeError):
    """Raised when a write is attempted within a read-only Unit of Work."""


class SQLAlchemyReadOnlyUnitOfWork(UnitOfWork):
    """
    Read-only Unit of Work backed by the Flask-scoped SQLAlchemy session.

    This UoW:
    - Optionally sets the transaction isolation level via
      ``execution_options(isolation_level=...)``.
    - Applies database-level READ ONLY (dialect-aware strategy) when enabled.
    - Installs portable write-guards and always rolls back on exit.
    - Disallows ``commit()`` by design.
    """

    def __init__(
        self,
        *,
        isolation_level: str | None = "READ COMMITTED",
        enforce_db_readonly: bool = True,
    ) -> None:

        self.session = db.session
        self.isolation_level = isolation_level
        self.enforce_db_readonly = enforce_db_readonly

        # Repository instances share the same session/transaction context.
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

        # Internal state
        self._conn: Connection | None = None
        self._trans = None
        self._dialect: str | None = None
        self._prev_autoflush: bool | None = None

        # Event listener function references (needed for proper removal).
        self._orm_flush_fn: Callable[[Any, Any, Any], None] | None = None
        self._core_sql_fn: Callable[[Any, Any, Any, Any, Any, Any], None] | None = None

        # Strategy will be chosen lazily in __enter__ (once we know the dialect).
        self._readonly_strategy: ReadOnlyStrategy = NoopReadOnlyStrategy()

    def __enter__(self) -> SQLAlchemyReadOnlyUnitOfWork:
        """
        Enter a read-only transactional scope.

        Steps
        -----
        1) Acquire a connection and set the requested isolation level.
        2) Pick and run the dialect-specific 'pre_begin' READ ONLY strategy.
        3) Begin the ORM transaction.
        4) Run the dialect-specific 'post_begin' READ ONLY strategy.
        5) Install write-guards and disable autoflush.
        """
        # 1) Connection + isolation
        self._conn = self.session.connection()
        self._dialect = self.session.bind.dialect.name if self.session.bind else None

        # Validate isolation level early
        if self._dialect and self.isolation_level not in VALID_ISOLATION_LEVELS_BY_DIALECT.get(
            self._dialect, set()
        ):
            raise ValueError(
                f"Isolation level '{self.isolation_level}' not supported for dialect '{self._dialect}'."
            )

        if self.isolation_level:
            self._conn = self._conn.execution_options(isolation_level=self.isolation_level)

        # 2) Strategy: pre-begin hook
        self._readonly_strategy = select_readonly_strategy(self._dialect, self.enforce_db_readonly)
        self._readonly_strategy.pre_begin(self._conn)

        # 3) Begin transaction at the Session level
        self._trans = self.session.begin()

        # 4) Strategy: post-begin hook
        self._readonly_strategy.post_begin(self.session)

        # 5) Guards + disable autoflush
        self._install_write_guards()
        self._prev_autoflush = self.session.autoflush
        self.session.autoflush = False

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Always roll back and remove guards.
        """
        try:
            self.rollback()
        finally:
            if self._prev_autoflush is not None:
                self.session.autoflush = self._prev_autoflush
            self._remove_write_guards()

    def commit(self) -> None:
        """
        Disallowed in a read-only Unit of Work.

        :raises ReadOnlyViolation: Always raised to signal misuse.
        """
        raise ReadOnlyViolation("commit() called on a read-only Unit of Work.")

    def rollback(self) -> None:
        """Roll back the current transaction (idempotent)."""
        try:
            if self._trans is not None:
                self._trans.rollback()
        finally:
            self._trans = None

    # ------------------------------ Write Guards ---------------------------- #

    def _install_write_guards(self) -> None:
        """
        Install ORM and Core level guards to detect writes.

        - ORM 'before_flush': blocks any pending changes (new/dirty/deleted).
        - Core 'before_cursor_execute': consults ExecutionContext flags to
          detect INSERT/UPDATE/DELETE, with a DDL fallback via simple prefix check.
        """

        def _raise_on_flush(session: Any, flush_context: Any, instances: Any) -> None:
            if session.new or session.dirty or session.deleted:
                raise ReadOnlyViolation(
                    "Attempted to flush changes inside a read-only Unit of Work."
                )

        def _raise_on_write_sql(
            conn: Connection,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            # Prefer ExecutionContext flags when present (more robust than string parsing).
            if context is not None and (
                getattr(context, "isinsert", False)
                or getattr(context, "isupdate", False)
                or getattr(context, "isdelete", False)
            ):
                raise ReadOnlyViolation("DML attempted inside a read-only Unit of Work.")

            # Fallback heuristic for DDL or raw text() statements.
            s = statement.lstrip().upper()
            if s.startswith(("CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME")):
                raise ReadOnlyViolation("DDL attempted inside a read-only Unit of Work.")

        # Keep function refs for proper removal
        self._orm_flush_fn = _raise_on_flush
        self._core_sql_fn = _raise_on_write_sql

        event.listen(self.session, "before_flush", self._orm_flush_fn)
        if self._conn is not None:
            event.listen(self._conn, "before_cursor_execute", self._core_sql_fn)

    def _remove_write_guards(self) -> None:
        """Detach event listeners to avoid leaking state across requests."""
        try:
            if self._orm_flush_fn is not None:
                event.remove(self.session, "before_flush", self._orm_flush_fn)
        except SQLAlchemyError:
            pass

        try:
            if self._conn is not None and self._core_sql_fn is not None:
                event.remove(self._conn, "before_cursor_execute", self._core_sql_fn)
        except SQLAlchemyError:
            pass
