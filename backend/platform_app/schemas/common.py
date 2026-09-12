"""
Common Pydantic Schemas

Shared DTOs used across multiple endpoints.
"""

from datetime import datetime
from pydantic import BaseModel


class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100


class PaginatedResponse(BaseModel):
    items: list
    total: int
    skip: int
    limit: int
    has_more: bool


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    socketio: str
    storage: str
    uptime: float | None = None
