"""
User Model

User accounts for the platform.
Phase 3 adds full authentication support.
Each user belongs to a Company (multi-tenant).
"""

from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid

from datetime import datetime


class User(Base, TimestampMixin, SoftDeleteMixin):
    """Platform user with full auth support."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
