# app/services/base.py
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.repositories.base import Pagination
from app.uow.sqlalchemy_uow import (
    SQLAlchemyReadOnlyUnitOfWork,
    SQLAlchemyUnitOfWork,
)


@dataclass(slots=True)
class ServiceContext:
    """
    Carry cross-cutting request-scoped data (auth, tenant, request ids, etc.).

    :param actor_id: Authenticated user identifier.
    :param tenant_id: Multi-tenant scoping identifier.
    :param request_id: Correlation id for logging/tracing.
    """

    actor_id: int | None = None
    tenant_id: int | None = None
    request_id: str | None = None


class BaseService:
    """
    Base class for application services.

    Responsibilities
    ----------------
    * Provide helpers to run read-only and read-write units of work.
    * Centralize error translation and logging.
    * Offer shared validation helpers (pagination/sorting).
    * Keep services thin, orchestration-only, no web/ORM leakage.

    Notes
    -----
    - Services must never touch the global session; always use a Unit of Work.
    - Domain/business rules live in the models (your design decision).
    """

    # ---- Configuration defaults (override per subclass if needed) ----
    DEFAULT_READ_ISOLATION = "READ COMMITTED"  # or "REPEATABLE READ"

    def __init__(self, *, ctx: ServiceContext | None = None) -> None:
        """
        Initialize the base service.

        :param ctx: Optional request-scoped context (auth, tenant, tracing).
        :type ctx: ServiceContext | None
        """
        self.ctx = ctx or ServiceContext()

    # -------------------------- UoW helpers ---------------------------------

    def rw_uow(self) -> SQLAlchemyUnitOfWork:
        """
        Create a read-write Unit of Work.

        :returns: Read-write UoW instance.
        :rtype: SQLAlchemyUnitOfWork
        """
        return SQLAlchemyUnitOfWork()

    def ro_uow(
        self, *, isolation: str | None = None, enforce_db_readonly: bool = True
    ) -> SQLAlchemyReadOnlyUnitOfWork:
        """
        Create a read-only Unit of Work.

        :param isolation: Transaction isolation level (e.g. "READ COMMITTED", "REPEATABLE READ").
        :type isolation: str | None
        :param enforce_db_readonly: Apply `SET TRANSACTION READ ONLY` when supported.
        :type enforce_db_readonly: bool
        :returns: Read-only UoW instance.
        :rtype: SQLAlchemyReadOnlyUnitOfWork
        """
        return SQLAlchemyReadOnlyUnitOfWork(
            isolation_level=isolation or self.DEFAULT_READ_ISOLATION,
            enforce_db_readonly=enforce_db_readonly,
        )

    # ----------------------- Validation utilities ---------------------------

    def ensure_pagination(
        self, *, page: int, limit: int, sort: Iterable[str] | None = None
    ) -> Pagination:
        """
        Build a Pagination value object with basic clamping.

        :param page: 1-based page number.
        :type page: int
        :param limit: Page size.
        :type limit: int
        :param sort: Sort tokens like ["-created_at", "name"].
        :type sort: Iterable[str] | None
        :returns: Pagination instance.
        :rtype: Pagination
        """
        page = max(1, int(page))
        limit = max(1, int(limit))
        return Pagination(page=page, limit=limit, sort=list(sort or []))

    # -------------------------- Error handling ------------------------------

    def translate_exceptions(self, exc: Exception) -> Exception:
        """
        Map low-level exceptions to application-level errors.

        .. note::
           Override in subclasses to translate IntegrityError, NotFound, etc.
        """
        return exc

    # --------------------------- ETag helpers -------------------------------

    def ensure_if_match(self, provided_etag: str | None, current_etag: str) -> None:
        """
        Validate If-Match precondition for optimistic concurrency.

        :param provided_etag: ETag provided by the client.
        :type provided_etag: str | None
        :param current_etag: Current entity ETag.
        :type current_etag: str
        :raises PermissionError: When ETag does not match.
        """
        if provided_etag is None or provided_etag != current_etag:
            raise PermissionError("Precondition failed: ETag mismatch.")

    # --------------------------- Idempotency hook ---------------------------

    def with_idempotency(self, key: str | None, fn: Callable[[], Any]) -> Any:
        """
        Optionally wrap a command with an idempotency policy (no-op default).

        :param key: Idempotency key (e.g., header).
        :type key: str | None
        :param fn: Callable to execute.
        :type fn: Callable[[], Any]
        :returns: Result of `fn`.
        :rtype: Any
        """
        # Hook: implement a store/cache if you adopt idempotency globally.
        return fn()
