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

- Identity service (from ``app.services.identity``)
    * :class:`IdentityService`
    * DTOs: :class:`UserRegisterIn`, :class:`UserAuthIn`, :class:`UserUpdateIn`,
      :class:`UserPasswordChangeIn`, :class:`UserPublicOut`, :class:`UserAuthOut`

- Subject service (from ``app.services.subjects``)
    * :class:`SubjectService`
    * DTOs: :class:`SubjectCreateIn`, :class:`SubjectLinkUserIn`,
      :class:`SubjectUnlinkUserIn`, :class:`SubjectUpdateProfileIn`,
      :class:`SubjectGetByPseudonymIn`, :class:`SubjectListIn`,
      :class:`SubjectPublicOut`, :class:`SubjectProfileOut`,
      :class:`SubjectWithProfileOut`, :class:`SubjectListOut`

- Subject metrics service (from ``app.services.subject_metrics``)
    * :class:`SubjectMetricsService`
    * DTOs: :class:`MetricsUpsertIn`, :class:`MetricsGetIn`,
      :class:`MetricsDeleteIn`, :class:`MetricsListIn`,
      :class:`MetricsRowOut`, :class:`MetricsListOut`
"""

from __future__ import annotations

# Base primitives (service base + request-scoped context)
from ._shared.base import BaseService, ServiceContext

# Shared DTOs (compose these in endpoint-specific DTOs)
from ._shared.dto import PageMeta, PaginationIn, ProblemDetails
from .identity.dto import (
    UserAuthIn,
    UserAuthOut,
    UserPasswordChangeIn,
    UserPublicOut,
    UserRegisterIn,
    UserUpdateIn,
)

# Identity service + DTOs
from .identity.service import IdentityService
from .subject_metrics.dto import (
    MetricsDeleteIn,
    MetricsGetIn,
    MetricsListIn,
    MetricsListOut,
    MetricsRowOut,
    MetricsUpsertIn,
)

# Subject metrics service + DTOs
from .subject_metrics.service import SubjectMetricsService
from .subjects.dto import (
    SubjectCreateIn,
    SubjectGetByPseudonymIn,
    SubjectLinkUserIn,
    SubjectListIn,
    SubjectListOut,
    SubjectProfileOut,
    SubjectPublicOut,
    SubjectUnlinkUserIn,
    SubjectUpdateProfileIn,
    SubjectWithProfileOut,
)

# Subject service + DTOs
from .subjects.service import SubjectService

__all__ = [
    # Base
    "BaseService",
    "ServiceContext",
    # Shared DTOs
    "PaginationIn",
    "PageMeta",
    "ProblemDetails",
    # Identity
    "IdentityService",
    "UserRegisterIn",
    "UserAuthIn",
    "UserUpdateIn",
    "UserPasswordChangeIn",
    "UserPublicOut",
    "UserAuthOut",
    # Subjects
    "SubjectService",
    "SubjectCreateIn",
    "SubjectLinkUserIn",
    "SubjectUnlinkUserIn",
    "SubjectUpdateProfileIn",
    "SubjectGetByPseudonymIn",
    "SubjectListIn",
    "SubjectPublicOut",
    "SubjectProfileOut",
    "SubjectWithProfileOut",
    "SubjectListOut",
    # Subject metrics
    "SubjectMetricsService",
    "MetricsUpsertIn",
    "MetricsGetIn",
    "MetricsDeleteIn",
    "MetricsListIn",
    "MetricsRowOut",
    "MetricsListOut",
]
