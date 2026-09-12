"""
Export Job Model — Simplified

Tracks export operations for lead batches.
Supports CSV and XLSX formats.
"""

import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJob(Base, TimestampMixin):
    """Tracks a lead export operation."""
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False, index=True
    )

    # Export configuration
    export_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="csv, xlsx"
    )
    selection_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="single_batch, selected_batches, all"
    )
    selected_batch_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Results
    lead_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=ExportStatus.PENDING.value, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
