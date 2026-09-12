"""
Lead Batch Keyword Model

Stores individual keywords associated with a search batch.
"""

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid


class LeadBatchKeyword(Base, TimestampMixin):
    """A keyword used in a lead batch search."""
    __tablename__ = "lead_batch_keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("lead_batches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    results_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    batch = relationship("LeadBatch", back_populates="keywords")
