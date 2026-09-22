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
    LeadProject,
    LeadRecord,
    LeadSearchResponse,
    LeadSource,
    MahaRERAEvidence,
    MahaRERAProject,
    WebsiteProject,
    WebsiteResearchEvidence,
)
from platform_app.services.contact_scraper import ContactScraper
from platform_app.services.maharera_verifier import MahaRERAVerifier
from platform_app.services.providers.registry import ProviderRegistry
from platform_app.services.search_strategy import SearchStrategyEngine
from platform_app.services.website_project_researcher import (
    WebsiteProjectResearcher,
)


class LeadCaptureService:
    """
    ATREAL Lead Discovery Pipeline.

    1. Google Maps / discovery providers
       -> builder + website + contact information

    2. Deduplicate builders within the search

    3. Builder website
       -> ongoing/upcoming/new projects only
       -> MahaRERA registration numbers

    4. MahaRERA
       -> verify each website-discovered registration number
       -> confirm project + promoter + location

    5. Rank all legitimate builders/projects

    No database is owned by this service.
    No Google Maps calls happen during enrichment.
    """

    def __init__(self):
        self.settings = get_settings()

        self.provider_registry = ProviderRegistry()

        self.strategy_engine = SearchStrategyEngine()

        self.scraper = ContactScraper(
            timeout=self.settings.SCRAPE_TIMEOUT_SECONDS,
            max_pages=self.settings.MAX_WEBSITE_PAGES,
        )

        self.maharera_verifier = MahaRERAVerifier(
            timeout=self.settings.SCRAPE_TIMEOUT_SECONDS,
        )

        self.website_project_researcher = WebsiteProjectResearcher(
            timeout=self.settings.SCRAPE_TIMEOUT_SECONDS,
            max_pages=self.settings.MAX_WEBSITE_PAGES,
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

        keywords = self._clean_keywords(keywords)
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

        strategy = await self.strategy_engine.generate_strategy(
            keywords=keywords,
            location=location,
        )

        providers = (
            await self.provider_registry
            .get_available_providers()
        )

        if not providers:
            raise RuntimeError(
                "No search providers are configured."
            )

        raw_results: list[dict[str, Any]] = []

        semaphore = asyncio.Semaphore(
            self.settings.MAX_CONCURRENT_RESEARCH
        )

        async def run_search(
            provider,
            keyword: str,
        ) -> list[dict[str, Any]]:

            async with semaphore:

                results: list[dict[str, Any]] = []
                page_token: str | None = None

                for page in range(
                    1,
                    self.settings.MAX_PAGES_PER_PROVIDER + 1,
                ):

                    if (
                        time.monotonic() - started
                        > self.settings.DISCOVERY_TIMEOUT_SECONDS
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
                                self.settings.MAX_SEARCH_RESULTS_PER_PROVIDER,
                                20,
                            ),
                            page=page,
                            page_token=page_token,
                        )

                    except Exception as exc:

                        print(
                            "[LeadCapture] "
                            f"{provider.name} failed "
                            f"for '{keyword}': "
                            f"{exc}"
                        )

                        break

                    for result in page_results:
                        results.append(
                            {
                                "raw": result,
                                "keyword": keyword,
                                "provider": provider.name,
                            }
                        )

                    if not next_token:
                        break

                    page_token = next_token

                return results

        tasks = [
            run_search(provider, keyword)
            for provider in providers
            for keyword in strategy.keywords
        ]

        completed = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        for result in completed:

            if isinstance(result, BaseException):
                print(
                    "[LeadCapture] "
                    f"Search task failed: {result}"
                )
                continue

            if isinstance(result, list):
                raw_results.extend(result)

        deduplicated = self._deduplicate_raw_results(
            raw_results
        )

        # Each builder is researched sequentially.
        # No Google Maps request occurs here.
        enriched = await self._enrich_results(
            deduplicated
        )

        leads: list[LeadRecord] = []

        for item in enriched:

            lead = self._build_lead(
                item,
                location,
            )

            if lead is not None:
                leads.append(lead)

        duplicates_removed = (
            len(raw_results)
            - len(deduplicated)
        )

        rejected = max(
            0,
            len(enriched) - len(leads),
        )

        providers_used = sorted(
            {
                item["provider"]
                for item in raw_results
            }
        )

        leads.sort(
            key=lambda lead: lead.ranking_score,
            reverse=True,
        )

        return LeadSearchResponse(
            location=location,
            keywords=keywords,
            leads=leads,
            stats=LeadDiscoveryStats(
                requested=limit,
                returned=len(leads),
                raw_results=len(raw_results),
                duplicates_removed=max(
                    0,
                    duplicates_removed,
                ),
                rejected=rejected,
                providers_used=providers_used,
            ),
        )

    # =============================================================
    # ENRICHMENT
    # =============================================================

    async def _enrich_results(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        enriched: list[dict[str, Any]] = []

        for index, item in enumerate(
            results,
            start=1,
        ):

            try:

                data = await self._enrich_single_result(
                    item
                )

                enriched.append(data)

                print(
                    "[LeadCapture] "
                    f"Processed builder "
                    f"{index}/{len(results)}: "
                    f"{data.get('business_name')}"
                )

            except Exception as exc:

                print(
                    "[LeadCapture] "
                    f"Builder enrichment failed: "
                    f"{exc}"
                )

                # Preserve the builder even if enrichment
                # fails. This allows legitimate low-priority
                # leads to remain in the result set.
                try:

                    fallback = self._raw_to_dict(
                        item["raw"],
                        item["keyword"],
                        item["provider"],
                    )

                    fallback["website_research"] = None
                    fallback["project_verifications"] = []

                    enriched.append(fallback)

                except Exception as fallback_exc:

                    print(
                        "[LeadCapture] "
                        f"Builder fallback failed: "
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

        # Preserve any metadata already accumulated
        # during deduplication.
        existing_keywords = item.get(
            "matched_keywords",
            [],
        )

        existing_sources = item.get(
            "sources",
            [],
        )

        if existing_keywords:
            data["matched_keywords"] = self._unique(
                existing_keywords
            )

        if existing_sources:
            data["sources"] = existing_sources

        business_name = (
            data.get("business_name")
            or ""
        )

        # ---------------------------------------------------------
        # STEP 1
        # Contact + website enrichment
        # ---------------------------------------------------------

        try:

            scraped = await self.scraper.extract_contacts(
                data
            )

        except Exception as exc:

            print(
                "[LeadCapture] "
                f"Contact scraping failed "
                f"for {business_name}: {exc}"
            )

            scraped = {}

        data["emails"] = (
            scraped.get("emails")
            or []
        )

        data["phones"] = (
            scraped.get("phone_numbers")
            or []
        )

        data["linkedin_url"] = scraped.get(
            "linkedin_url"
        )

        data["instagram_url"] = scraped.get(
            "instagram_url"
        )

        data["facebook_url"] = scraped.get(
            "facebook_url"
        )

        data["contact_name"] = scraped.get(
            "contact_name"
        )

        data["designation"] = scraped.get(
            "designation"
        )

        # ---------------------------------------------------------
        # STEP 2
        # Builder website -> active/upcoming projects
        # ---------------------------------------------------------

        website = data.get("website")

        try:

            website_research = (
                await self.website_project_researcher.research(
                    website=website,
                    business_name=business_name,
                )
            )

        except Exception as exc:

            print(
                "[LeadCapture] "
                f"Website research failed "
                f"for {business_name}: {exc}"
            )

            website_research = None

        data["website_research"] = website_research

        # ---------------------------------------------------------
        # STEP 3
        # Website RERA number -> MahaRERA
        #
        # Sequentially, one project at a time.
        # ---------------------------------------------------------

        project_verifications: list[
            dict[str, Any]
        ] = []

        if website_research is not None:

            for project in website_research.projects:

                registrations = (
                    project.maharera_registration_numbers
                    or (
                        [project.maharera_registration_number]
                        if project.maharera_registration_number
                        else []
                    )
                )

                # A project without a RERA number is intentionally
                # retained with null.
                if not registrations:

                    project_verifications.append(
                        {
                            "website_project": project,
                            "registration_number": None,
                            "verification": None,
                        }
                    )

                    continue

                # Verify every registration number published
                # on the project page.
                for registration_number in registrations:

                    try:

                        verification = (
                            await self.maharera_verifier.verify_registration(
                                registration_number=(
                                    registration_number
                                ),
                                project_name=project.name,
                                builder_name=business_name,
                                location=(
                                    project.location
                                    or data.get("address")
                                    or data.get("city")
                                ),
                            )
                        )

                    except Exception as exc:

                        print(
                            "[LeadCapture] "
                            f"MahaRERA verification "
                            f"failed for "
                            f"{registration_number}: "
                            f"{exc}"
                        )

                        verification = None

                    project_verifications.append(
                        {
                            "website_project": project,
                            "registration_number": (
                                registration_number
                            ),
                            "verification": verification,
                        }
                    )

        data["project_verifications"] = (
            project_verifications
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
            data.get("business_name")
        )

        if not business_name:
            return None

        if not self._looks_like_business(
            business_name
        ):
            return None

        website = data.get("website")
        domain = data.get("domain")

        emails = self._unique(
            data.get("emails") or []
        )

        phones = self._unique(
            data.get("phones") or []
        )

        sources: list[LeadSource] = []

        for source in data.get(
            "sources",
            [],
        ):

            sources.append(
                LeadSource(
                    provider=source["provider"],
                    url=source.get("url"),
                    matched_keyword=source.get(
                        "matched_keyword"
                    ),
                )
            )

        projects = self._build_projects(
            data
        )

        score, priority, reasons = self._rank(
            data=data,
            projects=projects,
            website=website,
            emails=emails,
            phones=phones,
        )

        has_contact = bool(
            emails or phones
        )

        # ---------------------------------------------------------
        # Aggregate MahaRERA evidence.
        # ---------------------------------------------------------

        verified_project_records = [
            item
            for item in data.get(
                "project_verifications",
                [],
            )
            if (
                item.get("verification") is not None
                and item["verification"].verified
            )
        ]

        all_rera_projects: list[
            MahaRERAProject
        ] = []

        maharera_evidence_lines: list[str] = []

        strongest_verification = None

        for item in data.get(
            "project_verifications",
            [],
        ):

            verification = item.get(
                "verification"
            )

            if verification is None:
                continue

            for project in verification.projects:

                all_rera_projects.append(
                    MahaRERAProject(
                        registration_number=(
                            project.registration_number
                        ),
                        project_name=(
                            project.project_name
                        ),
                        promoter_name=(
                            project.promoter_name
                        ),
                        location=(
                            project.location
                        ),
                        pincode=project.pincode,
                        district=project.district,
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

            maharera_evidence_lines.extend(
                verification.evidence
            )

            if (
                strongest_verification is None
                or verification.match_score
                > strongest_verification.match_score
            ):
                strongest_verification = verification

        if strongest_verification is not None:

            aggregate_maharera = MahaRERAEvidence(
                verified=bool(
                    verified_project_records
                ),
                match_type=(
                    strongest_verification.match_type
                ),
                match_score=(
                    strongest_verification.match_score
                ),
                promoter_name=(
                    strongest_verification.promoter_name
                ),
                projects=self._dedupe_maharera_projects(
                    all_rera_projects
                ),
                source_url=(
                    strongest_verification.source_url
                ),
                evidence=self._unique(
                    maharera_evidence_lines
                ),
            )

        else:

            aggregate_maharera = MahaRERAEvidence(
                verified=False,
                match_type="not_available",
                evidence=[
                    "No MahaRERA registration "
                    "number was available for "
                    "verification."
                ],
            )

        # ---------------------------------------------------------
        # Website evidence
        # ---------------------------------------------------------

        website_research = data.get(
            "website_research"
        )

        if website_research is not None:

            website_projects = [
                WebsiteProject(
                    name=project.name,
                    url=project.url,
                    location=project.location,
                    description=project.description,
                    status=project.status,
                    signals=project.signals,
                    evidence=project.evidence,
                    maharera_registration_number=(
                        project.maharera_registration_number
                    ),
                    maharera_registration_numbers=(
                        project.maharera_registration_numbers
                    ),
                )
                for project in website_research.projects
            ]

            website_evidence = WebsiteResearchEvidence(
                verified=website_research.verified,
                canonical_url=(
                    website_research.canonical_url
                ),
                company_identity_evidence=(
                    website_research.company_identity_evidence
                ),
                projects=website_projects,
            )

        else:

            website_evidence = WebsiteResearchEvidence(
                verified=False,
                canonical_url=website,
                projects=[],
            )

        evidence = LeadEvidence(
            signals=reasons,
            source_count=len(sources),
            website_verified=(
                bool(website)
                and (
                    website_research.verified
                    if website_research
                    else False
                )
            ),
            contact_verified=has_contact,
            maharera=aggregate_maharera,
            website_research=website_evidence,
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
            state=data.get("state"),
            country=data.get("country"),
            matched_keywords=self._unique(
                data.get(
                    "matched_keywords",
                    [],
                )
            ),
            sources=sources,
            rating=data.get("rating"),
            review_count=data.get(
                "review_count"
            ),
            place_id=data.get("place_id"),
            quality_status="valid",
            ranking_score=score,
            priority=priority,
            ranking_reasons=reasons,
            projects=projects,
            evidence=evidence,
        )

    # =============================================================
    # PROJECT BUILDING
    # =============================================================

    def _build_projects(
        self,
        data: dict[str, Any],
    ) -> list[LeadProject]:

        result: list[LeadProject] = []

        seen: set[tuple[str, str]] = set()

        for item in data.get(
            "project_verifications",
            [],
        ):

            project = item["website_project"]
            verification = item.get("verification")

            registration_number = (
                item.get("registration_number")
                or project.maharera_registration_number
            )

            key = (
                self._normalize_identity(
                    project.name
                ),
                registration_number or "",
            )

            if key in seen:
                continue

            seen.add(key)

            maharera_project = None

            if verification is not None:

                for candidate in verification.projects:

                    if (
                        candidate.registration_number
                        == registration_number
                    ):
                        maharera_project = candidate
                        break

                if (
                    maharera_project is None
                    and verification.projects
                ):
                    maharera_project = (
                        verification.projects[0]
                    )

            result.append(
                LeadProject(
                    name=project.name,
                    website_url=project.url,
                    location=project.location,
                    status=project.status,
                    signals=project.signals,
                    evidence=project.evidence,
                    maharera_registration_number=(
                        registration_number
                    ),
                    maharera_verified=(
                        verification.verified
                        if verification
                        else False
                    ),
                    maharera_match_type=(
                        verification.match_type
                        if verification
                        else (
                            "not_available"
                            if not registration_number
                            else "search_failed"
                        )
                    ),
                    maharera_match_score=(
                        verification.match_score
                        if verification
                        else 0
                    ),
                    maharera_project_name=(
                        maharera_project.project_name
                        if maharera_project
                        else None
                    ),
                    maharera_promoter_name=(
                        maharera_project.promoter_name
                        if maharera_project
                        else None
                    ),
                    maharera_location=(
                        maharera_project.location
                        if maharera_project
                        else None
                    ),
                    maharera_pincode=(
                        maharera_project.pincode
                        if maharera_project
                        else None
                    ),
                    maharera_district=(
                        maharera_project.district
                        if maharera_project
                        else None
                    ),
                    maharera_last_modified=(
                        maharera_project.last_modified
                        if maharera_project
                        else None
                    ),
                    maharera_source_url=(
                        verification.source_url
                        if verification
                        else None
                    ),
                    maharera_evidence=(
                        verification.evidence
                        if verification
                        else []
                    ),
                )
            )

        return result

    # =============================================================
    # RANKING
    # =============================================================

    def _rank(
        self,
        data: dict[str, Any],
        projects: list[LeadProject],
        website: str | None,
        emails: list[str],
        phones: list[str],
    ) -> tuple[
        float,
        str,
        list[str],
    ]:

        score = 0.0
        reasons: list[str] = []

        # ---------------------------------------------------------
        # 1. Builder fit — 25
        # ---------------------------------------------------------

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

        developer_terms = (
            "real estate developer",
            "property developer",
            "realty developer",
            "real estate development",
            "property development",
            "real estate builder",
            "property builder",
            "residential developer",
            "commercial developer",
            "developers",
            "developer",
            "builders",
            "builder",
        )

        if any(
            term in f"{name} {snippet}"
            for term in developer_terms
        ):

            score += 25

            reasons.append(
                "Real-estate builder/developer "
                "identified from discovery evidence."
            )

        # ---------------------------------------------------------
        # 2. Website — 20
        # ---------------------------------------------------------

        website_research = data.get(
            "website_research"
        )

        website_verified = bool(
            website
            and website_research
            and website_research.verified
        )

        if website_verified:

            score += 20

            reasons.append(
                "Builder website found and identity "
                "verified."
            )

        else:

            reasons.append(
                "Builder website is missing or "
                "could not be verified."
            )

        # ---------------------------------------------------------
        # 3. Active/upcoming project — 25
        # ---------------------------------------------------------

        active_projects = [
            project
            for project in projects
            if project.status in {
                "ongoing",
                "upcoming",
                "new_launch",
            }
        ]

        if active_projects:

            score += 25

            reasons.append(
                f"{len(active_projects)} active/upcoming "
                "project(s) found on the builder website."
            )

        else:

            reasons.append(
                "No active/upcoming project was "
                "confirmed on the builder website."
            )

        # ---------------------------------------------------------
        # 4. MahaRERA registration number — 15
        # ---------------------------------------------------------

        projects_with_rera = [
            project
            for project in projects
            if project.maharera_registration_number
        ]

        if projects_with_rera:

            score += 15

            reasons.append(
                "MahaRERA registration number found "
                "for at least one active/upcoming project."
            )

        else:

            reasons.append(
                "No MahaRERA registration number was "
                "found on the builder website."
            )

        # ---------------------------------------------------------
        # 5. MahaRERA builder/project verification — 15
        # ---------------------------------------------------------

        verified_projects = [
            project
            for project in projects
            if project.maharera_verified
        ]

        if verified_projects:

            score += 15

            reasons.append(
                "MahaRERA registration and builder/project "
                "identity verified."
            )

        # ---------------------------------------------------------
        # Priority
        #
        # Missing website OR missing RERA number means LOW.
        # We retain the lead; we do not reject it.
        # ---------------------------------------------------------

        if (
            not website_verified
            or not projects_with_rera
        ):

            priority = "low"

            reasons.append(
                "Low priority: website or MahaRERA "
                "registration evidence is missing."
            )

        elif verified_projects and active_projects:

            priority = "high"

            reasons.append(
                "High priority: verified builder website, "
                "active/upcoming project and MahaRERA evidence."
            )

        else:

            priority = "medium"

            reasons.append(
                "Medium priority: website and MahaRERA "
                "registration evidence found, but full "
                "verification is incomplete."
            )

        return (
            min(score, 100),
            priority,
            self._unique(reasons),
        )

    # =============================================================
    # VALIDATION
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
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

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

            if key not in canonical:

                normalized = self._raw_to_dict(
                    raw,
                    item["keyword"],
                    item["provider"],
                )

                # IMPORTANT:
                # Preserve the original discovery envelope.
                #
                # _enrich_single_result() expects:
                #   raw
                #   keyword
                #   provider
                #
                # The previous implementation removed those
                # fields during deduplication, causing:
                #
                #   KeyError: 'raw'
                #
                # Normalized fields remain alongside the
                # discovery envelope.

                canonical[key] = {
                    "raw": raw,
                    "keyword": item["keyword"],
                    "provider": item["provider"],
                    **normalized,
                }

                continue

            existing = canonical[key]

            keyword = item["keyword"]

            if keyword not in existing["matched_keywords"]:

                existing["matched_keywords"].append(
                    keyword
                )

            source = {
                "provider": item["provider"],
                "url": getattr(
                    raw,
                    "url",
                    None,
                ),
                "matched_keyword": keyword,
            }

            if source not in existing["sources"]:

                existing["sources"].append(
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
    # RAW RESULT
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

                domain = (
                    urlparse(url)
                    .netloc
                    .lower()
                    .removeprefix("www.")
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

    @staticmethod
    def _canonical_key(
        raw,
    ) -> str | None:

        place_id = getattr(
            raw,
            "place_id",
            None,
        )

        if place_id:
            return f"place:{place_id}"

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

            return f"domain:{domain}"

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
                return f"phone:{digits}"

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
            return f"name:{normalized}"

        return None

    # =============================================================
    # HELPERS
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
            result.append(keyword)

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

            value = str(value).strip()

            if not value:
                continue

            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)
            result.append(value)

        return result

    @staticmethod
    def _normalize_identity(
        value: str,
    ) -> str:

        value = value.casefold()

        value = re.sub(
            r"\b(private|pvt|limited|ltd|llp|llc)\b",
            " ",
            value,
        )

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

    @staticmethod
    def _dedupe_maharera_projects(
        projects: list[MahaRERAProject],
    ) -> list[MahaRERAProject]:

        seen: set[str] = set()
        result: list[MahaRERAProject] = []

        for project in projects:

            key = (
                project.registration_number
                or project.project_name
                or ""
            ).casefold()

            if not key or key in seen:
                continue

            seen.add(key)
            result.append(project)

        return result