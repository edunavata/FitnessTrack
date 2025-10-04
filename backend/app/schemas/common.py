"""Common Marshmallow schemas shared across resources."""

from __future__ import annotations

from typing import Any

from marshmallow import Schema, fields, post_load, validate


class SortQuerySchema(Schema):
    """Parse comma-separated ``sort`` query parameters into a list."""

    sort = fields.String(load_default="")

    @post_load
    def split_sort(self, data: dict[str, Any], **_: Any) -> dict[str, Any]:
        raw = data.get("sort") or ""
        tokens = [segment.strip() for segment in raw.split(",") if segment.strip()]
        data["sort"] = tokens
        return data


class PaginationQuerySchema(SortQuerySchema):
    """Validate pagination parameters with configurable defaults."""

    def __init__(self, *, default_limit: int = 20, max_limit: int = 200, **kwargs: Any) -> None:
        self._default_limit = default_limit
        self._max_limit = max_limit
        super().__init__(**kwargs)

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(validate=validate.Range(min=1))

    @post_load
    def apply_defaults(self, data: dict[str, Any], **_: Any) -> dict[str, Any]:
        sort_value = data.get("sort")
        if isinstance(sort_value, str):
            tokens = [segment.strip() for segment in sort_value.split(",") if segment.strip()]
            data["sort"] = tokens
        elif sort_value is None:
            data["sort"] = []
        limit = data.get("limit", self._default_limit)
        data["limit"] = min(max(limit, 1), self._max_limit)
        data.setdefault("page", 1)
        return data


class MetaSchema(Schema):
    """Metadata block for paginated responses."""

    total = fields.Integer(required=True)
    page = fields.Integer(required=True)
    limit = fields.Integer(required=True)


def build_meta(*, total: int, page: int, limit: int) -> dict[str, int]:
    """Return a ``meta`` mapping for paginated responses."""

    return {"total": int(total), "page": int(page), "limit": int(limit)}
