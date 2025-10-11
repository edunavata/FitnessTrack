# app/services/base.py
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.core import errors as api_errors
from app.repositories.base import Pagination
from app.services._shared.errors import (
    ConflictError,
    NotFoundError,
    PreconditionFailedError,
    ServiceError,
)
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
    :param sub_id: Subject pseudonym id.
    """

    actor_id: int | None = None
    tenant_id: int | None = None
    request_id: str | None = None
    subject_id: int | None = None


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
        Map domain/service-level errors to API-level (HTTP) errors.

        :param exc: Exception raised within the service.
        :type exc: Exception
        :returns: Translated exception ready to be re-raised.
        :rtype: Exception
        """
        # --- Domain <-> API translation ------------------------------------
        if isinstance(exc, NotFoundError):
            # → 404 Not Found
            return api_errors.NotFound(str(exc))

        if isinstance(exc, ConflictError):
            # → 409 Conflict
            return api_errors.Conflict(str(exc))

        if isinstance(exc, PreconditionFailedError):
            # → 412 Precondition Failed
            return api_errors.APIError(
                message=str(exc),
                status_code=412,
                code="precondition_failed",
            )

        # Any other ServiceError subclass → 400 Bad Request
        if isinstance(exc, ServiceError):
            return api_errors.APIError(
                message=str(exc),
                status_code=400,
                code="bad_request",
            )

        # Fallback: return untouched (will bubble up to Flask handler)
        return exc

    # --------------------------- ETag helpers -------------------------------

    def ensure_if_match(self, provided_etag: str | None, current_etag: str | None) -> None:
        """
        Validate If-Match precondition for optimistic concurrency.

        :param provided_etag: ETag provided by the client.
        :type provided_etag: str | None
        :param current_etag: Current entity ETag (``None`` when unsupported).
        :type current_etag: str | None
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

    # --------------------------- AuthZ --------------------------------
    def ensure_owner(self, actor_id: int | None, owner_id: int, *, msg: str | None = None) -> None:
        """
        Ensure the current actor is the resource owner. **actor_id** and **owner_id** should
        refer to the same type of entity (user or subject).

        :param actor_id: Authenticated actor (subject or user) id.
        :param owner_id: Expected owner (subject or user) id.
        :type owner_id: int
        :param msg: Optional custom error message.
        :type msg: str | None
        :raises AuthorizationError: If actor is not the owner.
        """
        # NOTE: Keep policy centralized here so services stay DRY.
        from app.services._shared.errors import AuthorizationError
        from app.services._shared.policies.common import is_owner

        if not is_owner(actor_id=actor_id, owner_id=owner_id):
            raise AuthorizationError(msg or "You can only access your own metrics.")
