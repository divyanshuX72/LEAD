"""
Authentication Models

JWT session tracking, roles, permissions, and user-company access.
"""

from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid

import enum


class RoleType(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    SALES = "sales"
    VIEWER = "viewer"


class Session(Base, TimestampMixin):
    """JWT session tracking for token management and revocation."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    token_jti: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        comment="JWT ID (jti claim) for token identification"
    )
    token_type: Mapped[str] = mapped_column(
        String(20), default="access", nullable=False,
        comment="access or refresh"
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class Role(Base, TimestampMixin):
    """Platform roles for access control."""
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="System roles cannot be deleted"
    )
    permissions_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="JSON array of permission strings"
    )


class Permission(Base):
    """Fine-grained permissions for future RBAC expansion."""
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Resource type: leads, companies, imports, exports, settings, etc."
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Action: create, read, update, delete, export, import"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)



