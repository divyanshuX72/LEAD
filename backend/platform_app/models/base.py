"""
Base Model

All ORM models inherit from this base. Provides:
- UUID primary keys
- Created/updated timestamps
- Soft-delete support
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SoftDeleteMixin:
    """Mixin that adds soft-delete support."""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())
