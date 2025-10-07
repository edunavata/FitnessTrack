# comments in English; reST docstrings strict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PaginationIn:
    """
    Input pagination contract.

    :param page: 1-based page number.
    :type page: int
    :param limit: Page size (> 0).
    :type limit: int
    :param sort: Sort tokens like ``["-created_at", "email"]``.
    :type sort: Iterable[str] | None
    """

    page: int = 1
    limit: int = 20
    sort: Iterable[str] | None = None


@dataclass(frozen=True, slots=True)
class PageMeta:
    """
    Output pagination metadata.

    :param page: Current page (1-based).
    :type page: int
    :param limit: Page size.
    :type limit: int
    :param total: Total rows available.
    :type total: int
    :param has_prev: Whether a previous page exists.
    :type has_prev: bool
    :param has_next: Whether a next page exists.
    :type has_next: bool
    """

    page: int
    limit: int
    total: int
    has_prev: bool
    has_next: bool


@dataclass(frozen=True, slots=True)
class ProblemDetails:
    """
    RFC 7807 problem details.

    :param type: URI reference that identifies the problem type.
    :type type: str
    :param title: Short, human-readable summary of the problem.
    :type title: str
    :param status: HTTP status code.
    :type status: int
    :param detail: Human-readable explanation.
    :type detail: str | None
    :param instance: URI reference that identifies the specific occurrence.
    :type instance: str | None
    :param extra: Optional extension members.
    :type extra: dict[str, Any] | None
    """

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    extra: dict[str, Any] | None = None
