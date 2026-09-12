"""
Search History Models

Tracks search sessions and individual queries.
Each session has an AI-generated strategy and multiple queries across providers.
"""

from sqlalchemy import String, Text, ForeignKey, JSON, Integer, BigInteger, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid
from datetime import datetime


class SearchSession(Base, TimestampMixin):
    """A lead discovery search session."""
    __tablename__ = "search_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False, index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="running", nullable=False,
        comment="running, completed, failed, cancelled"
    )

    # AI-generated strategy
    search_strategy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Results
    results_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    results_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    company = relationship("Company", foreign_keys=[company_id])
    queries = relationship("SearchQuery", back_populates="session", lazy="selectin", cascade="all, delete-orphan")


class SearchQuery(Base, TimestampMixin):
    """An individual search query executed within a session."""
    __tablename__ = "search_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("search_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Query details
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="serper, tavily, google_maps, brave, duckduckgo"
    )
    query_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Results
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False,
        comment="pending, running, completed, failed"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Raw results for debugging
    raw_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    session = relationship("SearchSession", back_populates="queries")
