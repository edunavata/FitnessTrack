"""
app.services._shared.ports
==========================

Collection of *ports* (hexagonal interfaces) that define the contracts
for token management and authentication infrastructure.

These ports decouple the domain/service layer from concrete implementations
of token issuing, revocation, and refresh storage mechanisms.

Modules
-------
- :mod:`token_provider`:
    Defines :class:`~.TokenProvider` — abstraction for JWT creation and decoding.

- :mod:`denylist_store`:
    Defines :class:`~.TokenDenylistStore` — interface for revocation and blacklist storage.

- :mod:`refresh_token_store`:
    Defines :class:`~.RefreshTokenStore`, :class:`~.RotationResult`,
    and :class:`~.RefreshSessionView` — abstractions for refresh-token rotation and persistence.

Design Notes
------------
All these ports follow *Dependency Inversion Principle (DIP)* to keep
the service layer independent from implementation details.
Concrete adapters (e.g., Redis, database, or in-memory stores) must
implement these interfaces under ``app.infra``.
"""

from __future__ import annotations

from .denylist_store import TokenDenylistStore
from .refresh_token_store import (
    InMemoryRefreshTokenStore,
    RefreshSessionView,
    RefreshTokenStore,
    RotationResult,
)

# Re-export core interfaces for clean imports
from .token_provider import StubTokenProvider, TokenProvider

__all__ = [
    "TokenProvider",
    "TokenDenylistStore",
    "RefreshTokenStore",
    "RotationResult",
    "RefreshSessionView",
    "InMemoryRefreshTokenStore",
    "StubTokenProvider",
]
