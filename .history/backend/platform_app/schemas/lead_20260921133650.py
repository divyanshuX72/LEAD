from __future__ import annotations

from pydantic import BaseModel, Field


class LeadSearchRequest(BaseModel):
    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
    )


class LeadSource(BaseModel):
    provider: str
    url: str | None = None
    matched_keyword: str | None = None


class MahaRERAProject(BaseModel):
    registration_number: str | None = None
    project_name: str | None = None
    promoter_name: str | None = None
    location: str | None = None
    pincode: str | None = None
    district: str | None = None
    last_modified: str | None = None
    details_url: str | None = None
    source_url: str | None = None


class MahaRERAEvidence(BaseModel):
    verified: bool = False
    match_type: str = "not_verified"
    match_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
    )
    promoter_name: str | None = None
    projects: list[MahaRERAProject] = Field(
        default_factory=list
    )
    source_url: str | None = None
    evidence: list[str] = Field(
        default_factory=list
    )


class WebsiteProject(BaseModel):
    name: str
    url: str
    location: str | None = None
    description: str | None = None
    signals: list[str] = Field(
        default_factory=list
    )
    evidence: list[str] = Field(
        default_factory=list
    )


class WebsiteResearchEvidence(BaseModel):
    verified: bool = False
    canonical_url: str | None = None
    company_identity_evidence: list[str] = Field(
        default_factory=list
    )
    projects: list[WebsiteProject] = Field(
        default_factory=list
    )


class LeadEvidence(BaseModel):
    signals: list[str] = Field(
        default_factory=list
    )
    source_count: int = 0
    website_verified: bool = False
    contact_verified: bool = False

    maharera: MahaRERAEvidence = Field(
        default_factory=MahaRERAEvidence
    )

    website_research: WebsiteResearchEvidence = Field(
        default_factory=WebsiteResearchEvidence
    )


class LeadRecord(BaseModel):
    business_name: str

    contact_name: str | None = None
    designation: str | None = None

    emails: list[str] = Field(
        default_factory=list
    )
    phones: list[str] = Field(
        default_factory=list
    )

    website: str | None = None
    domain: str | None = None

    linkedin_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None

    matched_keywords: list[str] = Field(
        default_factory=list
    )

    sources: list[LeadSource] = Field(
        default_factory=list
    )

    rating: float | None = None
    review_count: int | None = None
    place_id: str | None = None

    quality_status: str = "valid"

    ranking_score: float = Field(
        ge=0,
        le=100,
    )

    ranking_reasons: list[str] = Field(
        default_factory=list
    )

    evidence: LeadEvidence = Field(
        default_factory=LeadEvidence
    )


class LeadDiscoveryStats(BaseModel):
    requested: int
    returned: int
    raw_results: int
    duplicates_removed: int
    rejected: int
    providers_used: list[str] = Field(
        default_factory=list
    )


class LeadSearchResponse(BaseModel):
    success: bool = True

    agent: str = (
        "atreal_lead_capture_agent"
    )

    target_customer: str = (
        "Real Estate Developers"
    )

    location: str
    keywords: list[str]

    leads: list[LeadRecord]

    stats: LeadDiscoveryStats