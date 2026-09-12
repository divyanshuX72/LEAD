"""
Workspace & Organization Models

Workspace → Organization → Company hierarchy.
Prepares for future multi-tenant and Brain integration.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """Top-level organization entity."""
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    workspaces = relationship("Workspace", back_populates="organization", lazy="selectin")


class Workspace(Base, TimestampMixin, SoftDeleteMixin):
    """Workspace within an organization. Companies belong to workspaces."""
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization = relationship("Organization", back_populates="workspaces")
