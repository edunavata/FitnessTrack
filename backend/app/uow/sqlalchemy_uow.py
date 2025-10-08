"""
SQLAlchemy implementation of UnitOfWork for Flask.
"""

from __future__ import annotations

from contextlib import suppress

from flask import current_app
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError
from sqlalchemy.orm import Session, SessionTransaction

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


class SQLAlchemyRepositoryContainer:
    """Provide repository instances that share a SQLAlchemy session."""

    def __init__(self, *, session: Session) -> None:
        self.session = session
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


class SQLAlchemyUnitOfWork(SQLAlchemyRepositoryContainer, UnitOfWork):
    """
    SQLAlchemy-backed UoW using the Flask-scoped session.

    The same session is shared across all repositories for a consistent transaction.
    """

    def __init__(self) -> None:
        """Initialise the Unit of Work with a shared SQLAlchemy session.

        All repositories receive the same session instance so that they operate
        within the identical transactional context.
        """
        super().__init__(session=db.session)

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


class SQLAlchemyReadOnlyUnitOfWork(SQLAlchemyRepositoryContainer, UnitOfWork):
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
        super().__init__(session=db.session)
        self.isolation_level = isolation_level
        self.enforce_db_readonly = enforce_db_readonly

        # Internal state for listener lifecycle and transaction scope
        self._conn: Connection | None = None
        self._txn_ctx: SessionTransaction | None = None
        self._listeners_installed = False

    # ----------------------------- Context Manager -----------------------------

    def __enter__(self) -> SQLAlchemyReadOnlyUnitOfWork:
        """Enter a transactional scope that enforces read protections when possible.

        The unit of work first tries to own a fresh transaction so it can issue
        dialect-specific ``SET TRANSACTION`` directives that harden read-only
        semantics. If SQLAlchemy reports that a transaction is already running
        (``InvalidRequestError``), the scope gracefully attaches to that outer
        transaction instead of erroring. In that fallback path the guards still
        intercept ORM flushes and raw DML, but the effective permissions follow
        the parent transaction (which may allow writes). This compatibility
        behavior keeps sqlite-based tests from crashing on double-begin errors.
        """
        self._txn_ctx = None  # default: not owning the transaction
        self._conn = None
        self._is_nested = False  # optional flag if you want to track nesting

        try:
            # Attempt to own a new top-level transaction.
            txn_ctx = self.session.begin()
            txn_ctx.__enter__()  # enter context manager explicitly
            self._txn_ctx = txn_ctx  # we own this txn
        except InvalidRequestError:
            # A transaction is already begun on this Session (autobegin / outer fixture).
            # Do not start a new one; just attach to the existing scope and inherit its
            # read/write capabilities while still installing read guards.
            # We intentionally skip SET TRANSACTION directives here.
            pass

        # Grab the underlying Connection bound to the current session/txn
        self._conn = self.session.connection()
        dialect = self._conn.dialect.name

        # Install read-only guards regardless of owning or attaching
        self._install_listeners()

        # Apply SET TRANSACTION only if we own the top-level transaction
        if self._txn_ctx is not None:
            try:
                if self.isolation_level:
                    iso = self.isolation_level.upper().strip()
                    if iso not in (
                        "READ COMMITTED",
                        "REPEATABLE READ",
                        "SERIALIZABLE",
                        "READ UNCOMMITTED",
                    ):
                        current_app.logger.warning(
                            "Unknown isolation_level '%s'; attempting as-is.", iso
                        )
                    # Only meaningful on engines that support it and at top-level txn
                    self.session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {iso}"))

                if self.enforce_db_readonly and dialect in ("postgresql", "mysql", "mariadb"):
                    self.session.execute(text("SET TRANSACTION READ ONLY"))
            except SQLAlchemyError as exc:
                current_app.logger.warning(
                    "SET TRANSACTION directives failed (%s). Falling back to guards-only.", exc
                )

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Always remove guards. Roll back only if we own the transaction.
        """
        try:
            # If we created a txn in __enter__, we are responsible for closing it.
            if self._txn_ctx is not None:
                # Read-only scope → rollback to end our txn cleanly
                with suppress(Exception):
                    self.session.rollback()
                # Exit the SessionTransaction context we entered
                try:
                    self._txn_ctx.__exit__(exc_type, exc, tb)
                finally:
                    self._txn_ctx = None
        finally:
            # Detach listeners in any case (owned or attached)
            self._remove_listeners()
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
