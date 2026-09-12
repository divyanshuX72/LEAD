"""
Lead Source Model

Tracks when a lead is found across multiple search providers/sources.
"""

from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid


class LeadSource(Base, TimestampMixin):
    """Source record for a lead — one lead may have multiple sources."""
    __tablename__ = "lead_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    matched_keyword: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_identifier: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="sources")
