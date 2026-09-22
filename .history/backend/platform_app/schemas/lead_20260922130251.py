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

    # Regulatory information is kept separate from
    # promoter/project identity information.
    regulatory_status: str | None = None
    regulatory_notice: str | None = None


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

    status: str = "unknown"

    signals: list[str] = Field(
        default_factory=list
    )

    evidence: list[str] = Field(
        default_factory=list
    )

    maharera_registration_number: str | None = None

    maharera_registration_numbers: list[str] = Field(
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


class LeadProject(BaseModel):
    name: str

    website_url: str | None = None

    location: str | None = None

    status: str = "unknown"

    signals: list[str] = Field(
        default_factory=list
    )

    evidence: list[str] = Field(
        default_factory=list
    )

    maharera_registration_number: str | None = None

    maharera_verified: bool = False

    maharera_match_type: str = "not_verified"

    maharera_match_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
    )

    maharera_project_name: str | None = None

    maharera_promoter_name: str | None = None

    maharera_location: str | None = None

    maharera_pincode: str | None = None

    maharera_district: str | None = None

    maharera_last_modified: str | None = None

    maharera_source_url: str | None = None

    maharera_evidence: list[str] = Field(
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
        default=0.0,
        ge=0,
        le=100,
    )

    priority: str = "low"

    ranking_reasons: list[str] = Field(
        default_factory=list
    )

    projects: list[LeadProject] = Field(
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

    agent: str = "atreal_lead_capture_agent"

    target_customer: str = "Real Estate Developers"

    location: str

    keywords: list[str]

    leads: list[LeadRecord]

    stats: LeadDiscoveryStats


# ============================================================
# BUILDER DISCOVERY
# ============================================================


class BuilderDiscoveryRequest(BaseModel):
    """
    Request to discover UNIQUE new builders in a location.

    `target_limit` refers to accepted unique builders,
    not raw Google Maps results.
    """

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


class BuilderDiscoveryBuilder(BaseModel):
    business_name: str

    website: str | None = None

    phone: str | None = None

    address: str | None = None

    city: str | None = None

    state: str | None = None

    country: str | None = None

    rating: float | None = None

    review_count: int | None = None

    place_id: str | None = None

    maps_url: str | None = None

    matched_keyword: str | None = None

    lead_id: str | None = None

    company_id: str | None = None

    contact_id: str | None = None


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

    batch_id: str | None = None

    builders: list[BuilderDiscoveryBuilder] = Field(
        default_factory=list
    )