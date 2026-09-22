from __future__ import annotations

import asyncio
import re
import time
from typing import Any
from urllib.parse import urlparse

from platform_app.config.settings import get_settings
from platform_app.schemas.lead import (
    LeadDiscoveryStats,
    LeadEvidence,
    LeadRecord,
    LeadSearchResponse,
    LeadSource,
    MahaRERAEvidence,
    MahaRERAProject,
    WebsiteProject,
    WebsiteResearchEvidence,
)
from platform_app.services.contact_scraper import (
    ContactScraper,
)
from platform_app.services.maharera_verifier import (
    MahaRERAVerifier,
)
from platform_app.services.providers.registry import (
    ProviderRegistry,
)
from platform_app.services.search_strategy import (
    SearchStrategyEngine,
)
from platform_app.services.website_project_researcher import (
    WebsiteProjectResearcher,
)


class LeadCaptureService:
    """
    Stateless ATREAL Lead Discovery + Verification + Qualification.

    Pipeline:

        1. Search providers / Google Maps
                ↓
        2. Deduplicate discovered businesses
                ↓
        3. Research each builder one-by-one
                ↓
        4. MahaRERA verification
                ↓
        5. Builder's own website research
                ↓
        6. ATREAL qualification
                ↓
        7. Rank all legitimate leads

    Important:

    - No database.
    - No authentication.
    - No CRM persistence.
    - Google Maps is discovery only.
    - MahaRERA is regulatory/project verification.
    - Builder website is commercial/project intelligence.
    - Ranking does NOT delete leads.
    """

    def __init__(self):
        self.settings = get_settings()

        self.provider_registry = (
            ProviderRegistry()
        )

        self.strategy_engine = (
            SearchStrategyEngine()
        )

        self.scraper = ContactScraper(
            timeout=(
                self.settings
                .SCRAPE_TIMEOUT_SECONDS
            ),
            max_pages=(
                self.settings
                .MAX_WEBSITE_PAGES
            ),
        )

        self.maharera_verifier = (
            MahaRERAVerifier(
                timeout=(
                    self.settings
                    .SCRAPE_TIMEOUT_SECONDS
                ),
            )
        )

        self.website_project_researcher = (
            WebsiteProjectResearcher(
                timeout=(
                    self.settings
                    .SCRAPE_TIMEOUT_SECONDS
                ),
                max_pages=(
                    self.settings
                    .MAX_WEBSITE_PAGES
                ),
            )
        )

    # =============================================================
    # DISCOVERY
    # =============================================================

    async def discover(
        self,
        keywords: list[str],
        location: str,
        limit: int,
    ) -> LeadSearchResponse:

        started = time.monotonic()

        keywords = self._clean_keywords(
            keywords
        )

        location = location.strip()

        if not keywords:
            raise ValueError(
                "At least one valid keyword is required."
            )

        if not location:
            raise ValueError(
                "Location is required."
            )

        if limit < 1:
            raise ValueError(
                "Limit must be at least 1."
            )

        limit = min(
            limit,
            self.settings.MAX_SEARCH_LIMIT,
        )

        # ---------------------------------------------------------
        # Generate ATREAL discovery strategy
        # ---------------------------------------------------------

        strategy = (
            await self.strategy_engine
            .generate_strategy(
                keywords=keywords,
                location=location,
            )
        )

        # ---------------------------------------------------------
        # Get configured discovery providers
        # ---------------------------------------------------------

        providers = (
            await self.provider_registry
            .get_available_providers()
        )

        if not providers:
            raise RuntimeError(
                "No search providers are configured. "
                "Configure at least one of: "
                "Serper, Google Maps, Tavily, or Brave."
            )

        raw_results: list[
            dict[str, Any]
        ] = []

        # ---------------------------------------------------------
        # DISCOVERY CAN RUN CONCURRENTLY
        #
        # This is the only stage where we intentionally allow
        # concurrency.
        #
        # Verification happens one-by-one later.
        # ---------------------------------------------------------

        semaphore = asyncio.Semaphore(
            self.settings
            .MAX_CONCURRENT_RESEARCH
        )

        async def run_search(
            provider,
            keyword: str,
        ) -> list[dict[str, Any]]:

            async with semaphore:

                results: list[
                    dict[str, Any]
                ] = []

                page_token: str | None = None

                for page in range(
                    1,
                    self.settings
                    .MAX_PAGES_PER_PROVIDER
                    + 1,
                ):

                    # Respect global discovery timeout.
                    if (
                        time.monotonic()
                        - started
                        > self.settings
                        .DISCOVERY_TIMEOUT_SECONDS
                    ):
                        break

                    try:

                        (
                            page_results,
                            next_token,
                        ) = await provider.search(
                            keyword,
                            location=location,
                            limit=min(
                                self.settings
                                .MAX_SEARCH_RESULTS_PER_PROVIDER,
                                20,
                            ),
                            page=page,
                            page_token=page_token,
                        )

                    except Exception as exc:

                        print(
                            "[LeadCapture] "
                            f"{provider.name} "
                            f"failed for "
                            f"'{keyword}': {exc}"
                        )

                        break

                    for result in page_results:

                        results.append(
                            {
                                "raw": result,
                                "keyword": keyword,
                                "provider": (
                                    provider.name
                                ),
                            }
                        )

                    if not next_token:
                        break

                    page_token = next_token

                return results

        tasks = [
            run_search(
                provider,
                keyword,
            )
            for provider in providers
            for keyword in strategy.keywords
        ]

        completed = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        for result in completed:

            if isinstance(
                result,
                BaseException,
            ):

                print(
                    "[LeadCapture] "
                    f"Search task failed: {result}"
                )

                continue

            if not isinstance(
                result,
                list,
            ):
                continue

            raw_results.extend(
                result
            )

        # ---------------------------------------------------------
        # DEDUPLICATE
        # ---------------------------------------------------------

        deduplicated = (
            self._deduplicate_raw_results(
                raw_results
            )
        )

        # ---------------------------------------------------------
        # VERIFY + RESEARCH
        #
        # IMPORTANT:
        #
        # Each builder is processed one-by-one.
        #
        # Builder 1:
        #     contact/site
        #     → MahaRERA
        #     → own website
        #
        # Builder 2:
        #     contact/site
        #     → MahaRERA
        #     → own website
        #
        # etc.
        #
        # This prevents us from firing a large number of
        # MahaRERA / website requests simultaneously.
        # ---------------------------------------------------------

        enriched = (
            await self._enrich_results(
                deduplicated
            )
        )

        # ---------------------------------------------------------
        # BUILD FINAL LEADS
        # ---------------------------------------------------------

        leads: list[LeadRecord] = []

        for item in enriched:

            lead = self._build_lead(
                item,
                location,
            )

            if lead is not None:
                leads.append(lead)

        # ---------------------------------------------------------
        # STATS
        # ---------------------------------------------------------

        duplicates_removed = (
            len(raw_results)
            - len(deduplicated)
        )

        rejected = max(
            0,
            len(enriched)
            - len(leads),
        )

        providers_used = sorted(
            {
                item["provider"]
                for item in raw_results
            }
        )

        # ---------------------------------------------------------
        # RANK
        #
        # We sort the complete result set.
        #
        # We DO NOT remove lower-ranked leads.
        # ---------------------------------------------------------

        leads.sort(
            key=lambda lead: (
                lead.ranking_score
            ),
            reverse=True,
        )

        return LeadSearchResponse(
            location=location,
            keywords=keywords,
            leads=leads,
            stats=LeadDiscoveryStats(
                requested=limit,
                returned=len(leads),
                raw_results=len(
                    raw_results
                ),
                duplicates_removed=max(
                    0,
                    duplicates_removed,
                ),
                rejected=rejected,
                providers_used=(
                    providers_used
                ),
            ),
        )

    # =============================================================
    # ENRICHMENT / VERIFICATION
    # =============================================================

    async def _enrich_results(
        self,
        results: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:

        """
        Research builders sequentially.

        For every discovered builder:

            Google Maps result
                    ↓
            Existing contact/site extraction
                    ↓
            MahaRERA verification
                    ↓
            Builder website project research

        No Google Maps API call happens here.
        """

        enriched: list[
            dict[str, Any]
        ] = []

        for index, item in enumerate(
            results,
            start=1,
        ):

            try:

                data = (
                    await self._enrich_single_result(
                        item
                    )
                )

                enriched.append(data)

                business_name = (
                    data.get(
                        "business_name"
                    )
                    or "Unknown"
                )

                print(
                    "[LeadCapture] "
                    f"Verified builder "
                    f"{index}/{len(results)}: "
                    f"{business_name}"
                )

            except Exception as exc:

                print(
                    "[LeadCapture] "
                    f"Unexpected enrichment "
                    f"failure: {exc}"
                )

                # Preserve the discovered lead
                # even if enrichment fails.
                try:

                    fallback = (
                        self._raw_to_dict(
                            item["raw"],
                            item["keyword"],
                            item["provider"],
                        )
                    )

                    fallback[
                        "maharera"
                    ] = None

                    fallback[
                        "website_research"
                    ] = None

                    enriched.append(
                        fallback
                    )

                except Exception as fallback_exc:

                    print(
                        "[LeadCapture] "
                        f"Could not preserve "
                        f"failed lead: "
                        f"{fallback_exc}"
                    )

        return enriched

    async def _enrich_single_result(
        self,
        item: dict[str, Any],
    ) -> dict[str, Any]:

        raw = item["raw"]

        data = self._raw_to_dict(
            raw,
            item["keyword"],
            item["provider"],
        )

        business_name = (
            data.get(
                "business_name"
            )
            or ""
        )

        # =========================================================
        # STEP 1 — EXISTING WEBSITE / CONTACT ENRICHMENT
        # =========================================================

        try:

            scraped = (
                await self.scraper
                .extract_contacts(
                    data
                )
            )

        except Exception as exc:

            print(
                "[LeadCapture] "
                f"Contact scraping failed "
                f"for {business_name}: "
                f"{exc}"
            )

            scraped = {}

        data["emails"] = (
            scraped.get(
                "emails"
            )
            or []
        )

        data["phones"] = (
            scraped.get(
                "phone_numbers"
            )
            or []
        )

        data["linkedin_url"] = (
            scraped.get(
                "linkedin_url"
            )
        )

        data["instagram_url"] = (
            scraped.get(
                "instagram_url"
            )
        )

        data["facebook_url"] = (
            scraped.get(
                "facebook_url"
            )
        )

        data["contact_name"] = (
            scraped.get(
                "contact_name"
            )
        )

        data["designation"] = (
            scraped.get(
                "designation"
            )
        )

        # =========================================================
        # STEP 2 — MAHARERA
        # =========================================================

        try:

            maharera = (
                await self.maharera_verifier
                .verify(
                    business_name=(
                        business_name
                    ),
                    location=(
                        data.get(
                            "address"
                        )
                        or data.get(
                            "city"
                        )
                        or None
                    ),
                )
            )

        except Exception as exc:

            print(
                "[LeadCapture] "
                f"MahaRERA verification "
                f"failed for "
                f"{business_name}: "
                f"{exc}"
            )

            maharera = None

        data["maharera"] = (
            maharera
        )

        # =========================================================
        # STEP 3 — BUILDER'S OWN WEBSITE
        # =========================================================

        website = data.get(
            "website"
        )

        try:

            website_research = (
                await self
                .website_project_researcher
                .research(
                    website=website,
                    business_name=(
                        business_name
                    ),
                )
            )

        except Exception as exc:

            print(
                "[LeadCapture] "
                f"Builder website "
                f"research failed for "
                f"{business_name}: "
                f"{exc}"
            )

            website_research = None

        data["website_research"] = (
            website_research
        )

        return data

    # =============================================================
    # BUILD FINAL LEAD
    # =============================================================

    def _build_lead(
        self,
        data: dict[str, Any],
        location: str,
    ) -> LeadRecord | None:

        business_name = self._clean_text(
            data.get(
                "business_name"
            )
        )

        if not business_name:
            return None

        # This is only a basic sanity check.
        # It is NOT an ATREAL qualification filter.
        if not self._looks_like_business(
            business_name
        ):
            return None

        website = data.get(
            "website"
        )

        domain = data.get(
            "domain"
        )

        emails = self._unique(
            data.get(
                "emails"
            )
            or []
        )

        phones = self._unique(
            data.get(
                "phones"
            )
            or []
        )

        matched_keywords = self._unique(
            data.get(
                "matched_keywords",
                [],
            )
        )

        source_entries = data.get(
            "sources",
            [],
        )

        sources: list[
            LeadSource
        ] = []

        for source in source_entries:

            sources.append(
                LeadSource(
                    provider=(
                        source["provider"]
                    ),
                    url=source.get(
                        "url"
                    ),
                    matched_keyword=(
                        source.get(
                            "matched_keyword"
                        )
                    ),
                )
            )

        # ---------------------------------------------------------
        # ATREAL RANKING
        # ---------------------------------------------------------

        score, reasons = (
            self._rank(
                data=data,
                emails=emails,
                phones=phones,
                sources=sources,
            )
        )

        has_contact = bool(
            emails or phones
        )

        # ---------------------------------------------------------
        # MAHARERA EVIDENCE
        # ---------------------------------------------------------

        maharera = data.get(
            "maharera"
        )

        if maharera is not None:

            maharera_projects: list[
                MahaRERAProject
            ] = []

            for project in (
                maharera.projects
            ):

                maharera_projects.append(
                    MahaRERAProject(
                        registration_number=(
                            project
                            .registration_number
                        ),
                        project_name=(
                            project
                            .project_name
                        ),
                        promoter_name=(
                            project
                            .promoter_name
                        ),
                        location=(
                            project.location
                        ),
                        pincode=(
                            project.pincode
                        ),
                        district=(
                            project.district
                        ),
                        last_modified=(
                            project.last_modified
                        ),
                        details_url=(
                            project.details_url
                        ),
                        source_url=(
                            project.source_url
                        ),
                    )
                )

            maharera_evidence = (
                MahaRERAEvidence(
                    verified=(
                        maharera.verified
                    ),
                    match_type=(
                        maharera.match_type
                    ),
                    match_score=(
                        maharera.match_score
                    ),
                    promoter_name=(
                        maharera.promoter_name
                    ),
                    projects=(
                        maharera_projects
                    ),
                    source_url=(
                        maharera.source_url
                    ),
                    evidence=(
                        maharera.evidence
                    ),
                )
            )

        else:

            maharera_evidence = (
                MahaRERAEvidence(
                    verified=False,
                    match_type="not_verified",
                    match_score=0,
                    promoter_name=None,
                    projects=[],
                    source_url=None,
                    evidence=[
                        "MahaRERA verification "
                        "was unavailable for "
                        "this lead."
                    ],
                )
            )

        # ---------------------------------------------------------
        # BUILDER WEBSITE EVIDENCE
        # ---------------------------------------------------------

        website_research = data.get(
            "website_research"
        )

        if website_research is not None:

            website_projects: list[
                WebsiteProject
            ] = []

            for project in (
                website_research.projects
            ):

                website_projects.append(
                    WebsiteProject(
                        name=project.name,
                        url=project.url,
                        location=(
                            project.location
                        ),
                        description=(
                            project.description
                        ),
                        signals=(
                            project.signals
                        ),
                        evidence=(
                            project.evidence
                        ),
                    )
                )

            website_evidence = (
                WebsiteResearchEvidence(
                    verified=(
                        website_research
                        .verified
                    ),
                    canonical_url=(
                        website_research
                        .canonical_url
                    ),
                    company_identity_evidence=(
                        website_research
                        .company_identity_evidence
                    ),
                    projects=(
                        website_projects
                    ),
                )
            )

        else:

            website_evidence = (
                WebsiteResearchEvidence(
                    verified=False,
                    canonical_url=website,
                    company_identity_evidence=[],
                    projects=[],
                )
            )

        # ---------------------------------------------------------
        # FINAL EVIDENCE
        # ---------------------------------------------------------

        evidence = LeadEvidence(
            signals=reasons,
            source_count=len(
                sources
            ),
            website_verified=(
                bool(website)
                and (
                    website_research.verified
                    if website_research
                    else False
                )
            ),
            contact_verified=has_contact,
            maharera=(
                maharera_evidence
            ),
            website_research=(
                website_evidence
            ),
        )

        return LeadRecord(
            business_name=business_name,

            contact_name=data.get(
                "contact_name"
            ),

            designation=data.get(
                "designation"
            ),

            emails=emails,
            phones=phones,

            website=website,
            domain=domain,

            linkedin_url=data.get(
                "linkedin_url"
            ),

            instagram_url=data.get(
                "instagram_url"
            ),

            facebook_url=data.get(
                "facebook_url"
            ),

            address=data.get(
                "address"
            ),

            city=(
                data.get("city")
                or location
            ),

            state=data.get(
                "state"
            ),

            country=data.get(
                "country"
            ),

            matched_keywords=(
                matched_keywords
            ),

            sources=sources,

            rating=data.get(
                "rating"
            ),

            review_count=data.get(
                "review_count"
            ),

            place_id=data.get(
                "place_id"
            ),

            quality_status="valid",

            ranking_score=score,

            ranking_reasons=reasons,

            evidence=evidence,
        )

    # =============================================================
    # ATREAL RANKING
    # =============================================================

    def _rank(
        self,
        data: dict[str, Any],
        emails: list[str],
        phones: list[str],
        sources: list[LeadSource],
    ) -> tuple[
        float,
        list[str],
    ]:

        """
        ATREAL qualification model.

        Maximum score = 100.

        1. Real-estate developer fit      25
        2. MahaRERA evidence              25
        3. Construction/project timing    25
        4. Sales activity                 25

        Ranking NEVER removes a lead.
        """

        score = 0.0

        reasons: list[str] = []

        name = str(
            data.get(
                "business_name",
                "",
            )
        ).lower()

        snippet = str(
            data.get(
                "snippet",
                "",
            )
        ).lower()

        text = (
            f"{name} {snippet}"
        )

        # =========================================================
        # 1. REAL-ESTATE DEVELOPER FIT — 25
        # =========================================================

        developer_terms = (
            "real estate developer",
            "property developer",
            "property development",
            "real estate development",
            "realty developer",
            "residential developer",
            "commercial developer",
            "builder developer",
            "real estate builder",
            "property builder",
            "residential builder",
            "commercial builder",
            "realty group",
            "realty developers",
            "realty developer",
            "developers",
            "developer",
            "builders",
            "builder",
        )

        matched_developer_terms = [
            term
            for term in developer_terms
            if term in text
        ]

        if matched_developer_terms:

            score += 25

            reasons.append(
                "Real-estate developer fit "
                "identified from discovery "
                "evidence."
            )

        # =========================================================
        # 2. MAHARERA EVIDENCE — 25
        # =========================================================

        maharera = data.get(
            "maharera"
        )

        if maharera is not None:

            match_score = float(
                getattr(
                    maharera,
                    "match_score",
                    0,
                )
                or 0
            )

            verified = bool(
                getattr(
                    maharera,
                    "verified",
                    False,
                )
            )

            if (
                verified
                and match_score >= 90
            ):

                score += 25

                reasons.append(
                    "Strong MahaRERA "
                    "promoter/project "
                    "verification found."
                )

            elif (
                verified
                and match_score >= 80
            ):

                score += 20

                reasons.append(
                    "Probable MahaRERA "
                    "promoter/project "
                    "verification found."
                )

            elif match_score >= 65:

                score += 10

                reasons.append(
                    "Possible MahaRERA "
                    "match found; "
                    "manual verification "
                    "may be useful."
                )

        # =========================================================
        # 3. CONSTRUCTION / PROJECT TIMING — 25
        # =========================================================

        construction_points = 0

        website_research = data.get(
            "website_research"
        )

        all_signals: set[str] = set()

        if website_research is not None:

            projects = getattr(
                website_research,
                "projects",
                [],
            )

            for project in projects:

                project_signals = (
                    getattr(
                        project,
                        "signals",
                        [],
                    )
                    or []
                )

                all_signals.update(
                    project_signals
                )

        # Active construction is the strongest
        # current construction signal.
        if (
            "active_construction"
            in all_signals
        ):

            construction_points = max(
                construction_points,
                25,
            )

            reasons.append(
                "Builder website indicates "
                "active construction."
            )

        # Construction started.
        if (
            "construction_started"
            in all_signals
        ):

            construction_points = max(
                construction_points,
                20,
            )

            reasons.append(
                "Builder website indicates "
                "construction has started."
            )

        # New launch.
        if (
            "new_launch"
            in all_signals
        ):

            construction_points = max(
                construction_points,
                15,
            )

            reasons.append(
                "Builder website indicates "
                "a new project launch."
            )

        # Upcoming project.
        if (
            "upcoming"
            in all_signals
        ):

            construction_points = max(
                construction_points,
                15,
            )

            reasons.append(
                "Builder website indicates "
                "an upcoming project."
            )

        score += construction_points

        # =========================================================
        # 4. SALES ACTIVITY — 25
        # =========================================================

        sales_points = 0

        if (
            "booking_started"
            in all_signals
        ):

            sales_points = max(
                sales_points,
                25,
            )

            reasons.append(
                "Builder website indicates "
                "booking/sales activity."
            )

        if (
            "sales_activity"
            in all_signals
        ):

            sales_points = max(
                sales_points,
                20,
            )

            reasons.append(
                "Builder website contains "
                "current sales/project "
                "activity."
            )

        score += sales_points

        return (
            min(
                score,
                100,
            ),
            self._unique(
                reasons
            ),
        )

    # =============================================================
    # BASIC BUSINESS VALIDATION
    # =============================================================

    @staticmethod
    def _looks_like_business(
        name: str,
    ) -> bool:

        blocked = (
            "youtube",
            "wikipedia",
            "facebook",
            "instagram",
            "linkedin",
            "justdial",
            "indiamart",
            "olx",
        )

        lowered = name.lower()

        return not any(
            term in lowered
            for term in blocked
        )

    # =============================================================
    # DEDUPLICATION
    # =============================================================

    def _deduplicate_raw_results(
        self,
        results: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:

        canonical: dict[
            str,
            dict[str, Any],
        ] = {}

        for item in results:

            raw = item["raw"]

            key = self._canonical_key(
                raw
            )

            if not key:
                continue

            # -----------------------------------------------------
            # First occurrence
            # -----------------------------------------------------

            if key not in canonical:

                data = self._raw_to_dict(
                    raw,
                    item["keyword"],
                    item["provider"],
                )

                canonical[key] = data

                continue

            # -----------------------------------------------------
            # Duplicate occurrence
            # -----------------------------------------------------

            existing = canonical[key]

            keyword = item[
                "keyword"
            ]

            if keyword not in (
                existing[
                    "matched_keywords"
                ]
            ):

                existing[
                    "matched_keywords"
                ].append(
                    keyword
                )

            source = {
                "provider": (
                    item["provider"]
                ),
                "url": getattr(
                    raw,
                    "url",
                    None,
                ),
                "matched_keyword": (
                    keyword
                ),
            }

            if source not in (
                existing[
                    "sources"
                ]
            ):

                existing[
                    "sources"
                ].append(
                    source
                )

            self._merge_raw_fields(
                existing,
                raw,
            )

        return list(
            canonical.values()
        )

    # =============================================================
    # RAW RESULT → INTERNAL DICT
    # =============================================================

    def _raw_to_dict(
        self,
        raw,
        keyword: str,
        provider: str,
    ) -> dict[str, Any]:

        url = getattr(
            raw,
            "url",
            None,
        )

        domain = getattr(
            raw,
            "domain",
            None,
        )

        if not domain and url:

            try:

                hostname = (
                    urlparse(url)
                    .netloc
                    .lower()
                )

                domain = (
                    hostname.removeprefix(
                        "www."
                    )
                )

            except Exception:
                domain = None

        return {
            "business_name": (
                getattr(
                    raw,
                    "title",
                    None,
                )
                or ""
            ).strip(),

            "website": url,

            "domain": domain,

            "snippet": (
                getattr(
                    raw,
                    "snippet",
                    None,
                )
                or ""
            ),

            "phone": getattr(
                raw,
                "phone",
                None,
            ),

            "email": None,

            "address": getattr(
                raw,
                "address",
                None,
            ),

            "rating": getattr(
                raw,
                "rating",
                None,
            ),

            "review_count": getattr(
                raw,
                "review_count",
                None,
            ),

            "place_id": getattr(
                raw,
                "place_id",
                None,
            ),

            "city": None,
            "state": None,
            "country": None,

            "contact_name": None,
            "designation": None,

            "matched_keywords": [
                keyword
            ],

            "sources": [
                {
                    "provider": provider,
                    "url": url,
                    "matched_keyword": keyword,
                }
            ],
        }

    # =============================================================
    # MERGE DUPLICATE FIELDS
    # =============================================================

    @staticmethod
    def _merge_raw_fields(
        target: dict[str, Any],
        raw,
    ) -> None:

        for field in (
            "website",
            "domain",
            "phone",
            "address",
            "rating",
            "review_count",
            "place_id",
        ):

            if target.get(field):
                continue

            value = getattr(
                raw,
                field,
                None,
            )

            if value:
                target[field] = value

    # =============================================================
    # CANONICAL IDENTITY
    # =============================================================

    @staticmethod
    def _canonical_key(
        raw,
    ) -> str | None:

        # ---------------------------------------------------------
        # 1. Google Maps Place ID
        # ---------------------------------------------------------

        place_id = getattr(
            raw,
            "place_id",
            None,
        )

        if place_id:

            return (
                f"place:{place_id}"
            )

        # ---------------------------------------------------------
        # 2. Website domain
        # ---------------------------------------------------------

        domain = getattr(
            raw,
            "domain",
            None,
        )

        if domain:

            domain = (
                domain
                .lower()
                .strip()
            )

            domain = re.sub(
                r"^www\.",
                "",
                domain,
            )

            return (
                f"domain:{domain}"
            )

        # ---------------------------------------------------------
        # 3. Phone
        # ---------------------------------------------------------

        phone = getattr(
            raw,
            "phone",
            None,
        )

        if phone:

            digits = re.sub(
                r"\D",
                "",
                phone,
            )

            if len(digits) >= 8:

                return (
                    f"phone:{digits}"
                )

        # ---------------------------------------------------------
        # 4. Business name
        # ---------------------------------------------------------

        title = (
            getattr(
                raw,
                "title",
                None,
            )
            or ""
        )

        normalized = re.sub(
            r"[^a-z0-9]",
            "",
            title.lower(),
        )

        if normalized:

            return (
                f"name:{normalized}"
            )

        return None

    # =============================================================
    # INPUT CLEANING
    # =============================================================

    @staticmethod
    def _clean_keywords(
        keywords: list[str],
    ) -> list[str]:

        seen: set[str] = set()

        result: list[str] = []

        for keyword in keywords:

            keyword = re.sub(
                r"\s+",
                " ",
                keyword.strip(),
            )

            if not keyword:
                continue

            key = keyword.casefold()

            if key in seen:
                continue

            seen.add(key)

            result.append(
                keyword
            )

        return result

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        value = re.sub(
            r"\s+",
            " ",
            str(value).strip(),
        )

        return value or None

    @staticmethod
    def _unique(
        values: list[str],
    ) -> list[str]:

        result: list[str] = []

        seen: set[str] = set()

        for value in values:

            if not value:
                continue

            value = str(
                value
            ).strip()

            if not value:
                continue

            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)

            result.append(
                value
            )

        return result