"""
Domain-level exceptions used within the service layer.

These exceptions are **framework-agnostic** and should never import or depend
on Flask, HTTP, or SQLAlchemy directly. They serve as stable contracts between
repositories, domain models, and application services.

The translation to HTTP responses (RFC 7807) is handled by
``app/core/errors.py`` via ``BaseService.translate_exceptions()``.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Base types
# --------------------------------------------------------------------------- #


class ServiceError(Exception):
    """
    Base class for all service-level errors.

    Notes
    -----
    - These are *not* HTTP errors.
    - They can be safely raised from repositories or domain logic.
    - The API layer or BaseService will later translate them to APIError.
    """

    pass


# --------------------------------------------------------------------------- #
# Specific domain-level errors
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class NotFoundError(ServiceError):
    """
    Raised when an entity is not found in the repository.

    :param entity: Entity name (e.g., "User").
    :type entity: str
    :param key: Identifier or search key.
    :type key: str | int
    """

    entity: str
    key: str | int

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.entity} not found: {self.key}"


@dataclass(slots=True)
class ConflictError(ServiceError):
    """
    Raised when a unique constraint or business rule conflict occurs.

    :param entity: Entity name (e.g., "User").
    :type entity: str
    :param detail: Short human-readable explanation.
    :type detail: str
    """

    entity: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover
        return f"Conflict on {self.entity}: {self.detail}"


class PreconditionFailedError(ServiceError):
    """
    Raised when preconditions such as ETag ``If-Match`` validation fail.
    """

    def __init__(self, message: str = "Precondition failed (ETag mismatch)") -> None:
        super().__init__(message)
