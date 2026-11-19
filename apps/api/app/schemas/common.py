"""Common schemas and consistent error responses."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Consistent error format across all endpoints."""

    error_code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class MessageResponse(BaseModel):
    """Simple confirmation or message response."""

    message: str
    status: str = "ok"


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    total: int
    limit: int
    offset: int
    has_more: bool
