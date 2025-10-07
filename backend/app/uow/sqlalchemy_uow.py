"""
SQLAlchemy implementation of UnitOfWork for Flask.
"""

from __future__ import annotations

from contextlib import suppress

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import SessionTransaction

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


class SQLAlchemyReadOnlyUnitOfWork(UnitOfWork):
    """
    Read-only Unit of Work backed by the Flask-scoped SQLAlchemy session.

    This UoW:
    - Optionally sets the transaction isolation level via
      ``SET TRANSACTION ISOLATION LEVEL <...>`` (dialect-aware).
    - Applies database-level READ ONLY when enabled (``SET TRANSACTION READ ONLY``).
    - Installs portable write-guards and always rolls back on exit.
    - Disallows ``commit()`` by design.

    Parameters
    ----------
    isolation_level:
        Optional transaction isolation level hint. Common values:
        ``"READ COMMITTED"`` (default) or ``"REPEATABLE READ"``.
        If ``None``, the connection's default is used.
    enforce_db_readonly:
        If ``True`` (default), applies ``SET TRANSACTION READ ONLY`` when supported.

    Notes
    -----
    *PostgreSQL*: fully supported (read-only + isolation).
    *MySQL/MariaDB*: ``SET TRANSACTION READ ONLY`` supported on modern versions.
    *SQLite*: read-only flag is not supported; write-guards still prevent writes.
    """

    # Guard patterns for portable "no write" at driver level
    _WRITE_PREFIXES = (
        "insert",
        "update",
        "delete",
        "merge",
        "alter",
        "drop",
        "truncate",
        "create",
        "replace",
        "grant",
        "revoke",
    )

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

        # Internal state for listener lifecycle and transaction scope
        self._conn: Connection | None = None
        self._txn_ctx: SessionTransaction | None = None
        self._listeners_installed = False

    # ----------------------------- Context Manager -----------------------------

    def __enter__(self) -> SQLAlchemyReadOnlyUnitOfWork:
        """
        Enter a read-only transactional scope.

        Steps:
        1. Begin an explicit transaction on the session.
        2. Install write-guards to block ORM flushes and raw DML/DDL.
        3. Apply dialect-aware ``SET TRANSACTION`` directives for isolation and read-only.
        """
        # 1) Begin an explicit transaction right away to guarantee snapshot semantics.
        #    Using a session transaction ensures subsequent queries run under this scope.
        txn_ctx = self.session.begin()
        self._txn_ctx = txn_ctx
        txn_ctx.__enter__()  # enter context manager manually

        # 2) Grab the underlying Connection bound to this session transaction.
        self._conn = self.session.connection()
        dialect = self._conn.dialect.name

        # 3) Install write-guards (portable).
        self._install_listeners()

        # 4) Apply transaction characteristics as early as possible in the txn.
        #    Use dialect-aware statements; ignore if not supported.
        try:
            if self.isolation_level:
                # Standard SQL form supported by PostgreSQL and MySQL/MariaDB.
                iso = self.isolation_level.upper().strip()
                if iso not in (
                    "READ COMMITTED",
                    "REPEATABLE READ",
                    "SERIALIZABLE",
                    "READ UNCOMMITTED",
                ):
                    # Keep permissive but warn in logs; do not explode in runtime.
                    db.logger.warning("Unknown isolation_level '%s'; attempting as-is.", iso)
                self.session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {iso}"))

            if self.enforce_db_readonly and dialect in ("postgresql", "mysql", "mariadb"):
                # SQLite doesn't support it; others may — best effort.
                self.session.execute(text("SET TRANSACTION READ ONLY"))
        except SQLAlchemyError as exc:
            # If SET TRANSACTION is not supported, we keep the RO guard semantics
            # and continue in read-only mode enforced by listeners.
            db.logger.warning(
                "SET TRANSACTION directives failed (%s). Falling back to guards-only.", exc
            )

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Always roll back, remove listeners, and close the transactional scope.
        """
        try:
            # No commit in RO mode; always rollback to end the transaction.
            self.rollback()
        finally:
            self._remove_listeners()
            # Exit the session transaction context if we manually entered it.
            if self._txn_ctx is not None:
                try:
                    self._txn_ctx.__exit__(exc_type, exc, tb)
                finally:
                    self._txn_ctx = None
            self._conn = None

    # ----------------------------- Public API ---------------------------------

    def commit(self) -> None:
        """
        Disallow commit in read-only Unit of Work.

        :raises RuntimeError: always, to prevent accidental writes.
        """
        raise RuntimeError("Read-only UnitOfWork does not allow commit().")

    def rollback(self) -> None:
        """Rollback the current transaction if active."""
        try:
            self.session.rollback()
        except Exception:
            # Best-effort rollback; re-raise to surface issues upstream if needed.
            raise

    # ----------------------------- Guards & Listeners --------------------------

    def _install_listeners(self) -> None:
        """Install ORM/db-level listeners to prevent any write attempt."""
        if self._listeners_installed:
            return

        # 1) Block ORM flushes that would emit DML.
        def _before_flush(session, flush_context, instances):
            if session.new or session.dirty or session.deleted:
                raise RuntimeError(
                    "Read-only UnitOfWork: ORM flush blocked (new/dirty/deleted objects present)."
                )

        event.listen(self.session, "before_flush", _before_flush)

        # 2) Block raw DML/DDL at cursor level (covers text() / core emits).
        def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            first_token = statement.lstrip().split(None, 1)[0].lower() if statement else ""
            if first_token.startswith(self._WRITE_PREFIXES):
                raise RuntimeError(
                    f"Read-only UnitOfWork: SQL statement blocked: {first_token.upper()}"
                )

        # Bind the listener to the *Connection* if available, else Engine.
        target = self._conn if self._conn is not None else self.session.get_bind()
        event.listen(target, "before_cursor_execute", _before_cursor_execute)

        # Keep refs for removal
        self._ro__before_flush = _before_flush
        self._ro__before_cursor_execute = _before_cursor_execute
        self._listeners_installed = True

    def _remove_listeners(self) -> None:
        """Detach previously installed listeners."""
        if not self._listeners_installed:
            return

        with suppress(Exception):
            event.remove(self.session, "before_flush", self._ro__before_flush)

        with suppress(Exception):
            target = self._conn if self._conn is not None else self.session.get_bind()
            event.remove(target, "before_cursor_execute", self._ro__before_cursor_execute)

        self._listeners_installed = False
