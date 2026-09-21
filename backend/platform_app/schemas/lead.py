from pydantic import BaseModel, Field


class LeadSearchRequest(BaseModel):
    """
    Stateless lead discovery request.

    The Main Agent supplies the discovery intent.
    The Lead Agent performs discovery and returns results.
    """

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


class LeadEvidence(BaseModel):
    signals: list[str] = Field(default_factory=list)
    source_count: int = 0
    website_verified: bool = False
    contact_verified: bool = False


class LeadRecord(BaseModel):
    """
    Discovery result.

    This is NOT a CRM record and is NOT persisted by this service.
    """

    business_name: str

    contact_name: str | None = None
    designation: str | None = None

    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)

    website: str | None = None
    domain: str | None = None

    linkedin_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None

    matched_keywords: list[str] = Field(default_factory=list)

    sources: list[LeadSource] = Field(default_factory=list)

    rating: float | None = None
    review_count: int | None = None
    place_id: str | None = None

    quality_status: str = "valid"

    ranking_score: float = Field(
        ge=0,
        le=100,
    )

    ranking_reasons: list[str] = Field(default_factory=list)

    evidence: LeadEvidence = Field(
        default_factory=LeadEvidence
    )


class LeadDiscoveryStats(BaseModel):
    requested: int
    returned: int
    raw_results: int
    duplicates_removed: int
    rejected: int
    providers_used: list[str] = Field(default_factory=list)


class LeadSearchResponse(BaseModel):
    success: bool = True

    agent: str = "atreal_lead_capture_agent"

    target_customer: str = "Real Estate Developers"

    location: str

    keywords: list[str]

    leads: list[LeadRecord]

    stats: LeadDiscoveryStats