"""
Lead Model — Simplified

Core entity representing a discovered business lead.
Focused on contact discovery and export — no CRM, scoring, or AI analysis.
"""

from sqlalchemy import String, Text, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid


class Lead(Base, TimestampMixin):
    """A discovered business lead."""
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False, index=True
    )
    batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("lead_batches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Business identity
    business_name: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contact
    emails: Mapped[list[str]] = mapped_column(JSON, default=list)
    phones: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Web presence
    website: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    x_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Location
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Discovery metadata
    matched_keyword: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_primary: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Ratings
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quality
    quality_status: Mapped[str] = mapped_column(
        String(50), default="valid", nullable=False,
        comment="valid, suspect, invalid"
    )
    verification_status: Mapped[str] = mapped_column(
        String(50), default="unverified", nullable=False,
        comment="unverified, verified, failed"
    )

    # Deduplication
    dedupe_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)

    # Relationships
    batch = relationship("LeadBatch", back_populates="leads")
    sources = relationship(
        "LeadSource", back_populates="lead",
        lazy="selectin", cascade="all, delete-orphan"
    )
