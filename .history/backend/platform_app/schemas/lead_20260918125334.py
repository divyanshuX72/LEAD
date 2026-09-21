"""
Lead Agent Pydantic Schemas — Simplified

Request/Response DTOs for lead discovery, batches, and exports.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ── Lead Search Request ──────────────────────────────────────────────────

class LeadSearchRequest(BaseModel):
    """Request to start a lead discovery search."""
    keywords: list[str] = Field(
        ..., min_length=1, max_length=20,
        description="Keywords to search for (e.g., ['Dentist', 'Dental Clinic'])"
    )
    location: str = Field(
        ..., min_length=1,
        description="Location to search in (e.g., 'Mumbai')"
    )
    limit: int = Field(
        50, ge=1, le=500,
        description="Number of leads to find"
    )


# ── Lead Batch ───────────────────────────────────────────────────────────

class LeadBatchResponse(BaseModel):
    id: str
    name: str
    location: str
    requested_count: int
    raw_results_count: int
    duplicate_count: int
    rejected_count: int
    final_count: int
    status: str
    reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    keywords: list[str] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_keywords(cls, batch) -> "LeadBatchResponse":
        kw_list = [kw.keyword for kw in (batch.keywords or [])]
        return cls(
            id=batch.id,
            name=batch.name,
            location=batch.location,
            requested_count=batch.requested_count,
            raw_results_count=batch.raw_results_count,
            duplicate_count=batch.duplicate_count,
            rejected_count=batch.rejected_count,
            final_count=batch.final_count,
            status=batch.status,
            reason=batch.reason,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            keywords=kw_list,
        )


class LeadBatchDetailResponse(LeadBatchResponse):
    """Batch with embedded leads list."""
    leads: list["LeadResponse"] = []


# ── Lead ─────────────────────────────────────────────────────────────────

class LeadResponse(BaseModel):
    id: str
    batch_id: str
    business_name: str
    contact_name: str | None = None
    designation: str | None = None
    emails: list[str] = []
    phones: list[str] = []
    website: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    x_url: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    matched_keyword: str | None = None
    source_primary: str | None = None
    source_url: str | None = None
    rating: float | None = None
    review_count: int | None = None
    quality_status: str = "valid"
    verification_status: str = "unverified"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Export ────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str = Field("csv", description="Export format: csv or xlsx")
    unique_only: bool = Field(False, description="For 'all' exports: deduplicate across batches")


class ExportSelectedRequest(ExportRequest):
    batch_ids: list[str] = Field(..., min_length=1, description="Batch IDs to export")


class ExportResponse(BaseModel):
    id: str
    export_type: str
    selection_type: str
    lead_count: int
    status: str
    file_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard Stats ──────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_leads: int = 0
    total_batches: int = 0
    last_search: datetime | None = None
    unique_emails: int = 0
    unique_phones: int = 0


# ── Search Progress (for SSE / Socket.IO) ────────────────────────────────

class SearchProgress(BaseModel):
    batch_id: str
    status: str
    current_keyword: str | None = None
    keywords_completed: int = 0
    keywords_total: int = 0
    leads_found: int = 0
    leads_target: int = 0
    message: str = ""
