"""
Lead Batch Model

Each lead search creates a separate batch (folder).
Tracks search parameters, progress, and final statistics.
Multi-tenant: scoped to company_id.
"""

import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid


class BatchStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


class LeadBatch(Base, TimestampMixin):
    """A lead discovery search batch / folder."""
    __tablename__ = "lead_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)

    # Counts
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    raw_results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    final_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=BatchStatus.PENDING.value, nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Stop reason: target_achieved, timeout, no_more_results, providers_exhausted"
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    keywords = relationship(
        "LeadBatchKeyword", back_populates="batch",
        lazy="selectin", cascade="all, delete-orphan"
    )
    leads = relationship(
        "Lead", back_populates="batch",
        lazy="noload", cascade="all, delete-orphan"
    )
