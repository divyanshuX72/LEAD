from __future__ import annotations

from pydantic import BaseModel, Field


class BuilderDiscoveryRequest(BaseModel):
    workspace_id: str = Field(
        min_length=1,
        max_length=100,
    )
    location: str = Field(
        min_length=1,
        max_length=255,
    )
    target_limit: int = Field(
        default=20,
        ge=1,
        le=500,
    )


class BuilderEvidence(BaseModel):
    source_type: str
    source_url: str | None = None
    field: str
    value: str | None = None
    reason: str | None = None


class BuilderDiscoveryBuilder(BaseModel):
    business_name: str

    domain: str | None = None
    website: str | None = None

    phones: list[str] = Field(
        default_factory=list
    )
    emails: list[str] = Field(
        default_factory=list
    )

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    place_id: str | None = None
    maps_url: str | None = None

    rating: float | None = None
    review_count: int | None = None

    qualification_status: str
    qualification_reasons: list[str] = Field(
        default_factory=list
    )

    matched_keyword: str | None = None
    matched_keywords: list[str] = Field(
        default_factory=list
    )

    provider: str = "google_maps"

    evidence: list[BuilderEvidence] = Field(
        default_factory=list
    )


class BuilderDiscoveryResponse(BaseModel):
    success: bool = True
    agent: str = "atreal_lead_capture_agent"
    discovery_type: str = "builder"

    workspace_id: str
    location: str

    requested: int
    returned: int

    raw_results: int
    duplicates_removed: int
    rejected: int

    discovery_exhausted: bool

    providers_used: list[str] = Field(
        default_factory=list
    )

    queries_used: list[str] = Field(
        default_factory=list
    )

    builders: list[BuilderDiscoveryBuilder] = Field(
        default_factory=list
    )