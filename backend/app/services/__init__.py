"""Service layer public API.

This package exposes the essential building blocks for the service layer so that
callers can import from :mod:`app.services` without knowing internal structure.

Re-exports
----------
- Base primitives (from ``app.services._shared.base``)
    * :class:`BaseService`
    * :class:`ServiceContext`

- Shared DTOs (from ``app.services._shared.dto``)
    * :class:`PaginationIn`
    * :class:`PageMeta`
    * :class:`ProblemDetails`
"""

from __future__ import annotations

# Base primitives (service base + request-scoped context)
from ._shared.base import BaseService, ServiceContext

# Shared DTOs (compose these in endpoint-specific DTOs)
from ._shared.dto import PageMeta, PaginationIn, ProblemDetails

__all__ = [
    # Base
    "BaseService",
    "ServiceContext",
    # Shared DTOs
    "PaginationIn",
    "PageMeta",
    "ProblemDetails",
]
