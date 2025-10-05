"""Generic repository base and query utilities for SQLAlchemy 2.x.

This module centralizes persistence-only concerns shared by all repositories:
- Strongly-typed pagination and sorting helpers.
- Safe sorting with a whitelist mapping (prevents SQL injection).
- Deterministic pagination (adds primary-key tiebreaker).
- Optional total counting with an optimized strategy.
- Eager-loading hooks to prevent N+1 issues.
- Safe update helpers with per-repository updatable-field whitelists.
- No business logic, no commit/rollback — Services own transactions.

Design decisions
----------------
* Repositories MUST remain thin and persistence-focused:
  - They never implement use cases or domain policies.
  - They never call commit/rollback; Services define the Unit of Work.
* Sorting is opt-in per aggregate via ``_sortable_fields`` mapping.
* Eager-loading is opt-in via ``_default_eagerload`` to avoid N+1.
* ``selectinload`` is preferred for 1:N, ``joinedload`` for 1:1 by subclasses.
* Updates MUST NOT allow mass-assignment: each repo exposes an explicit
  ``_updatable_fields`` whitelist.

"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.extensions import db

E = TypeVar("E")  # SQLAlchemy mapped entity type


# ------------------------------- Pagination ----------------------------------


@dataclass(slots=True)
class Pagination:
    """Pagination input parameters.

    :param page: 1-based page number (validated to be ``>= 1``).
    :type page: int
    :param limit: Page size (validated to be ``>= 1``).
    :type limit: int
    :param sort: Public sort tokens (e.g., ``["-created_at", "name"]``).
    :type sort: list[str]
    """

    page: int
    limit: int
    sort: list[str]


@dataclass(slots=True)
class Page(Generic[E]):
    """Result page with metadata.

    :param items: Listed entities in the current page.
    :type items: Sequence[E]
    :param total: Total item count for the query (when computed).
    :type total: int
    :param page: 1-based current page number.
    :type page: int
    :param limit: Page size.
    :type limit: int
    """

    items: Sequence[E]
    total: int
    page: int
    limit: int


# ----------------------------- Sorting utilities -----------------------------


def parse_sort_tokens(raw: Iterable[str]) -> list[tuple[str, bool]]:
    """Parse public sort tokens into ``(field, is_desc)`` tuples.

    :param raw: Public tokens like ``["-created_at", "name"]``.
    :type raw: Iterable[str]
    :returns: List of ``(field_name, is_desc)`` tokens.
    :rtype: list[tuple[str, bool]]
    """
    parsed: list[tuple[str, bool]] = []
    for token in raw:
        is_desc = token.startswith("-")
        field = token[1:] if is_desc else token
        field = field.strip()
        if field:
            parsed.append((field, is_desc))
    return parsed


def _apply_sorting(
    stmt: Select[Any],
    sortable_fields: Mapping[str, InstrumentedAttribute[Any]],
    tokens: Iterable[str],
    *,
    pk_attr: InstrumentedAttribute[Any] | None,
) -> Select[Any]:
    """Apply safe ``ORDER BY`` clauses based on a whitelist mapping.

    Unknown sort tokens are ignored silently. The model's primary key is always
    appended as a final ascending tiebreaker to stabilize pagination.

    :param stmt: Base selectable.
    :type stmt: :class:`sqlalchemy.sql.Select`
    :param sortable_fields: Public field → SQLAlchemy attribute mapping.
    :type sortable_fields: Mapping[str, InstrumentedAttribute]
    :param tokens: Public sort tokens (e.g., ``["-created_at"]``).
    :type tokens: Iterable[str]
    :param pk_attr: Primary-key attribute used as a tiebreaker.
    :type pk_attr: InstrumentedAttribute | None
    :returns: Modified select with ``ORDER BY`` clauses.
    :rtype: :class:`sqlalchemy.sql.Select`
    """
    orders: list[Any] = []
    for field, is_desc in parse_sort_tokens(tokens):
        col = sortable_fields.get(field)
        if isinstance(col, InstrumentedAttribute):
            orders.append(col.desc() if is_desc else col.asc())

    if orders:
        stmt = stmt.order_by(*orders)

    # Always add PK as a final tiebreaker to stabilize pagination
    if pk_attr is not None:
        stmt = stmt.order_by(pk_attr.asc())

    return stmt


# --------------------------- Pagination execution ----------------------------


def paginate_select(
    session: Session,
    stmt: Select[Any],
    *,
    page: int,
    limit: int,
    with_total: bool = True,
) -> tuple[list[Any], int]:
    """Execute a select with pagination and an optional total count.

    The statement's existing ``ORDER BY`` is stripped for the ``COUNT`` to avoid
    unnecessary sorting overhead.

    :param session: Active SQLAlchemy session.
    :type session: :class:`sqlalchemy.orm.Session`
    :param stmt: Base select to paginate (already filtered/sorted).
    :type stmt: :class:`sqlalchemy.sql.Select`
    :param page: 1-based page number (will be clamped to ``>= 1``).
    :type page: int
    :param limit: Page size (will be clamped to ``>= 1``).
    :type limit: int
    :param with_total: Whether to compute the total row count.
    :type with_total: bool
    :returns: Tuple of ``(items, total)`` where ``total`` is 0 when ``with_total=False``.
    :rtype: tuple[list[Any], int]
    """
    page = max(int(page), 1)
    limit = max(int(limit), 1)

    total = 0
    if with_total:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int(session.execute(count_stmt).scalar_one())

    offset = (page - 1) * limit
    sliced = stmt.limit(limit).offset(offset)
    items = list(session.execute(sliced).scalars().all())
    return items, total


# ------------------------------ Base repository ------------------------------


class BaseRepository(Generic[E]):
    """Generic, persistence-only repository for a single aggregate.

    Subclasses MUST define:

    * ``model``: the SQLAlchemy mapped class.

    Subclasses MAY override:

    * ``_sortable_fields`` to expose safe sort keys.
    * ``_default_eagerload`` to attach eager-loading options.
    * ``_filterable_fields`` to enable filter whitelisting (recommended).
    * ``_updatable_fields`` to whitelist keys allowed for updates.
    * ``_soft_delete`` to implement soft deletions.

    This class NEVER:

    * opens/commits/rolls back transactions,
    * implements business rules or cross-aggregate coordination.

    Services orchestrate use cases and own transaction boundaries.
    """

    #: SQLAlchemy mapped model (must be set by subclasses)
    model: type[E]

    def __init__(self, session: Session | None = None) -> None:
        """Initialise the repository with an optional SQLAlchemy session.

        When no explicit session is provided the repository falls back to the
        Flask-scoped session exposed by ``app.core.extensions``.

        :param session: Session shared across the Unit of Work scope.
        :type session: :class:`sqlalchemy.orm.Session` | None
        """
        self._session: Session | None = session

    # ------------------------------ Session access ---------------------------

    @property
    def session(self) -> Session:
        """Return the active SQLAlchemy session.

        Prefers the injected session when provided; otherwise uses the
        Flask-scoped session managed by the extension.

        :returns: Active session bound to the current Unit of Work.
        :rtype: :class:`sqlalchemy.orm.Session`
        """
        if self._session is not None:
            return self._session
        return cast(Session, db.session)

    # ------------------------------ Extensibility ----------------------------

    def _default_eagerload(self, stmt: Select[Any]) -> Select[Any]:
        """Attach eager-loading options to generic get/list operations.

        Subclasses can add ``joinedload``/``selectinload`` depending on
        cardinality (1:1 vs 1:N) to prevent N+1 issues.

        :param stmt: Base select.
        :type stmt: :class:`sqlalchemy.sql.Select`
        :returns: Potentially modified select with eager options.
        :rtype: :class:`sqlalchemy.sql.Select`
        """
        return stmt

    def _soft_delete(self, instance: E) -> bool:
        """Hook for soft deletion. Return ``True`` if deletion was handled.

        Subclasses can override to mark a ``deleted_at`` flag or similar.

        :param instance: Entity to delete.
        :type instance: E
        :returns: ``True`` when soft-deleted; ``False`` to perform hard delete.
        :rtype: bool
        """
        return False

    def _pk_attr(self) -> InstrumentedAttribute[Any] | None:
        """Return the model's primary-key ``InstrumentedAttribute`` if available.

        Defaults to ``model.id`` when present.

        :returns: PK attribute or ``None``.
        :rtype: :class:`sqlalchemy.orm.InstrumentedAttribute` | None
        """
        return getattr(self.model, "id", None)

    def _sortable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]]:
        """Whitelist mapping of public sort keys to model attributes.

        Subclasses should override and expose only safe, indexed columns.

        :returns: Public key → ORM attribute mapping.
        :rtype: Mapping[str, InstrumentedAttribute]
        """
        return {}

    def _filterable_fields(self) -> Mapping[str, InstrumentedAttribute[Any]] | None:
        """Optional whitelist of equality-filterable fields.

        **Compatibility mode (default)**:
            If this method returns ``None``, equality filters are applied by
            accessing attributes directly via ``getattr(self.model, key) == value``.
            This preserves legacy behavior where any model attribute can be used.

        **Whitelist mode (recommended)**:
            If a mapping is returned, only keys present in the map are applied.
            Unknown keys are silently ignored.

        :returns: Public key → ORM attribute mapping, or ``None`` for legacy mode.
        :rtype: Mapping[str, InstrumentedAttribute] | None
        """
        return None

    def _updatable_fields(self) -> set[str]:
        """Whitelist of public keys that can be assigned on update.

        Subclasses **should** override this to prevent mass-assignment.
        Example:
            ``return {"sex", "birth_year", "height_cm", "dominant_hand"}``

        :returns: Set of allowed public keys for update operations.
        :rtype: set[str]
        """
        return set()

    # ------------------------------ Internals --------------------------------

    def _apply_equality_filters(
        self,
        stmt: Select[Any],
        filters: Mapping[str, Any] | None,
    ) -> Select[Any]:
        """Apply equality filters using whitelist or legacy behavior.

        If ``_filterable_fields()`` returns a mapping, only those keys are applied.
        If it returns ``None``, legacy behavior applies all keys via ``getattr``.

        :param stmt: Input select to filter.
        :type stmt: :class:`sqlalchemy.sql.Select`
        :param filters: Field=value mapping (equality only).
        :type filters: Mapping[str, Any] | None
        :returns: Filtered select.
        :rtype: :class:`sqlalchemy.sql.Select`
        """
        if not filters:
            return stmt

        allowed = self._filterable_fields()
        if allowed is None:
            clauses = [getattr(self.model, k) == v for k, v in filters.items()]
            return stmt.where(and_(*clauses)) if clauses else stmt

        whitelist_clauses: list[Any] = []
        for k, v in filters.items():
            col = allowed.get(k)
            if isinstance(col, InstrumentedAttribute):
                whitelist_clauses.append(col == v)
        return stmt.where(and_(*whitelist_clauses)) if whitelist_clauses else stmt

    def _sanitize_update_fields(
        self,
        fields: Mapping[str, Any],
        *,
        strict: bool = True,
    ) -> dict[str, Any]:
        """Return a dict with only whitelisted update keys.

        :param fields: Raw update mapping (public keys).
        :type fields: Mapping[str, Any]
        :param strict: When ``True``, raise ``ValueError`` on unknown keys.
                       When ``False``, ignore unknown keys silently.
        :type strict: bool
        :returns: Filtered mapping with only allowed keys.
        :rtype: dict[str, Any]
        :raises ValueError: If ``strict`` and unknown keys are present.
        """
        allowed = self._updatable_fields()
        if not allowed:
            # Fail-closed by default to avoid accidental mass-assignment
            if fields and strict:
                raise ValueError("No updatable fields configured for this repository.")
            return {}

        unknown = [k for k in fields if k not in allowed]
        if unknown and strict:
            raise ValueError(f"Unknown or non-updatable fields: {unknown}")

        return {k: v for k, v in fields.items() if k in allowed}

    # --------------------------------- CRUD ----------------------------------

    def add(self, instance: E) -> E:
        """Stage a new entity for persistence and flush to materialize the PK.

        :param instance: New entity instance.
        :type instance: E
        :returns: The same instance after ``flush()``.
        :rtype: E
        """
        self.session.add(instance)
        self.flush()
        return instance

    def get(self, entity_id: Any) -> E | None:
        """Retrieve a single entity by primary key.

        :param entity_id: Primary-key value.
        :type entity_id: Any
        :returns: Entity or ``None``.
        :rtype: E | None
        :raises RuntimeError: If no PK attribute can be detected.
        """
        pk_attr = self._pk_attr()
        if pk_attr is None:
            raise RuntimeError("BaseRepository.get requires a detectable PK attribute.")
        stmt = self._default_eagerload(select(self.model).where(pk_attr == entity_id))
        result = self.session.execute(stmt).scalars().first()
        return cast(E | None, result)

    def get_for_update(self, entity_id: Any) -> E | None:
        """Retrieve an entity by PK with a ``FOR UPDATE`` lock (when supported).

        :param entity_id: Primary-key value.
        :type entity_id: Any
        :returns: Locked entity or ``None``.
        :rtype: E | None
        :raises RuntimeError: If no PK attribute can be detected.
        """
        pk_attr = self._pk_attr()
        if pk_attr is None:
            raise RuntimeError("BaseRepository.get_for_update requires a detectable PK.")
        stmt = self._default_eagerload(
            select(self.model).where(pk_attr == entity_id)
        ).with_for_update()
        result = self.session.execute(stmt).scalars().first()
        return cast(E | None, result)

    def find_one(self, **filters: Any) -> E | None:
        """Find a single entity by simple equality filters.

        Honors the whitelist if ``_filterable_fields()`` is defined.

        :param filters: Field=value pairs (equality only).
        :type filters: dict[str, Any]
        :returns: Entity or ``None``.
        :rtype: E | None
        """
        stmt: Select[Any] = select(self.model)
        stmt = self._apply_equality_filters(stmt, filters)
        stmt = self._default_eagerload(stmt)
        result = self.session.execute(stmt).scalars().first()
        return cast(E | None, result)

    def exists(self, **filters: Any) -> bool:
        """Check existence for simple equality filters.

        Honors the whitelist if ``_filterable_fields()`` is defined.

        :param filters: Field=value pairs (equality only).
        :type filters: dict[str, Any]
        :returns: ``True`` when at least one row matches, else ``False``.
        :rtype: bool
        """
        stmt: Select[Any] = select(func.true()).select_from(self.model)
        stmt = self._apply_equality_filters(stmt, filters)
        return bool(self.session.execute(stmt.limit(1)).scalar())

    def delete(self, instance: E) -> None:
        """Delete an entity (soft or hard) and flush changes.

        :param instance: Entity to delete.
        :type instance: E
        """
        if not self._soft_delete(instance):
            self.session.delete(instance)
        self.flush()

    def flush(self) -> None:
        """Flush pending changes to the database without committing.

        :returns: ``None``.
        :rtype: None
        """
        self.session.flush()

    # ----------------------------- Safe updates -------------------------------

    def assign_updates(
        self,
        instance: E,
        fields: Mapping[str, Any],
        *,
        strict: bool = True,
        flush: bool = True,
    ) -> E:
        """Assign only whitelisted keys to ``instance`` and optionally flush.

        The assignment uses ``setattr`` to trigger SQLAlchemy ``@validates``
        decorators defined on the mapped class.

        :param instance: Entity to mutate.
        :type instance: E
        :param fields: Public mapping of fields to assign.
        :type fields: Mapping[str, Any]
        :param strict: Raise on unknown keys (recommended True).
        :type strict: bool
        :param flush: Call ``session.flush()`` after assignment.
        :type flush: bool
        :returns: The mutated instance.
        :rtype: E
        :raises ValueError: If ``strict`` and unknown keys are present, or if no
                           updatable fields are configured.
        """
        updates = self._sanitize_update_fields(fields, strict=strict)
        for k, v in updates.items():
            setattr(instance, k, v)
        if flush:
            self.flush()
        return instance

    def update(self, instance: E, **fields: Any) -> E:
        """Convenience wrapper around :meth:`assign_updates` with defaults.

        :param instance: Entity to mutate.
        :type instance: E
        :param fields: Public mapping of fields to assign.
        :type fields: Any
        :returns: The mutated instance.
        :rtype: E
        """
        return self.assign_updates(instance, fields, strict=True, flush=True)

    # ------------------------------- Listing ---------------------------------

    def list(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        sort: Iterable[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[E]:
        """List entities with optional filtering and sorting.

        * Honors the whitelist provided by ``_filterable_fields()``.
        * Applies eager-loading via ``_default_eagerload()``.
        * Applies safe sorting with primary-key tiebreaker.

        :param filters: Equality filters (public keys).
        :type filters: Mapping[str, Any] | None
        :param sort: Public sort tokens (e.g., ``["-created_at"]``).
        :type sort: Iterable[str] | None
        :param limit: Optional limit.
        :type limit: int | None
        :param offset: Optional offset.
        :type offset: int | None
        :returns: List of entities.
        :rtype: list[E]
        """
        stmt: Select[Any] = select(self.model)
        stmt = self._apply_equality_filters(stmt, filters)
        stmt = self._default_eagerload(stmt)
        stmt = _apply_sorting(stmt, self._sortable_fields(), sort or [], pk_attr=self._pk_attr())

        if limit is not None:
            stmt = stmt.limit(int(limit))
        if offset is not None:
            stmt = stmt.offset(int(offset))

        results = self.session.execute(stmt).scalars().all()
        return cast(list[E], list(results))

    def paginate(
        self,
        pagination: Pagination,
        *,
        filters: Mapping[str, Any] | None = None,
        with_total: bool = True,
    ) -> Page[E]:
        """Paginate entities with stable sorting and optional total.

        * Honors the whitelist provided by ``_filterable_fields()``.
        * Applies eager-loading via ``_default_eagerload()``.
        * Applies safe sorting with primary-key tiebreaker.

        :param pagination: Pagination parameters.
        :type pagination: Pagination
        :param filters: Equality filters (public keys).
        :type filters: Mapping[str, Any] | None
        :param with_total: Whether to compute total rows.
        :type with_total: bool
        :returns: :class:`Page` with items and metadata.
        :rtype: Page[E]
        """
        stmt: Select[Any] = select(self.model)
        stmt = self._apply_equality_filters(stmt, filters)
        stmt = self._default_eagerload(stmt)
        stmt = _apply_sorting(
            stmt, self._sortable_fields(), pagination.sort, pk_attr=self._pk_attr()
        )

        raw_items, total = paginate_select(
            self.session,
            stmt,
            page=pagination.page,
            limit=pagination.limit,
            with_total=with_total,
        )
        items = cast(list[E], raw_items)
        return Page(
            items=items,
            total=total if with_total else 0,
            page=pagination.page,
            limit=pagination.limit,
        )
