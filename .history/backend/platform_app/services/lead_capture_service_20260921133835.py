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
)
from platform_app.services.contact_scraper import (
    ContactScraper,
)
from platform_app.services.providers.registry import (
    ProviderRegistry,
)
from platform_app.services.search_strategy import (
    SearchStrategyEngine,
)
from platform_app.services.maharera_verifier import (
    MahaRERAVerifier,
)
from platform_app.services.website_project_researcher import (
    WebsiteProjectResearcher,
)

class LeadCaptureService:
    """
    Stateless ATREAL lead discovery engine.

    No database.
    No authentication.
    No CRM persistence.

    The service discovers, enriches, validates,
    deduplicates, and ranks leads, then returns
    them to the caller.
    """

    def __init__(self):
        self.settings = get_settings()

        self.provider_registry = ProviderRegistry()

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
        self.maharera_verifier = MahaRERAVerifier(
    timeout=self.settings.SCRAPE_TIMEOUT_SECONDS,
    )

    self.website_project_researcher = (
        WebsiteProjectResearcher(
            timeout=self.settings.SCRAPE_TIMEOUT_SECONDS,
            max_pages=self.settings.MAX_WEBSITE_PAGES,
        )
    )

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

        strategy = (
            await self.strategy_engine
            .generate_strategy(
                keywords=keywords,
                location=location,
            )
        )

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

        semaphore = asyncio.Semaphore(
            self.settings
            .MAX_CONCURRENT_RESEARCH
        )

        async def run_search(
            provider,
            keyword: str,
        ):
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
                            f"failed: {exc}"
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

            raw_results.extend(result)

        deduplicated = (
            self._deduplicate_raw_results(
                raw_results
            )
        )

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
            len(enriched)
            - len(leads),
        )

        providers_used = sorted(
            {
                item["provider"]
                for item in raw_results
            }
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

    async def _enrich_results(
        self,
        results: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:

        semaphore = asyncio.Semaphore(
            self.settings
            .MAX_CONCURRENT_RESEARCH
        )

        async def enrich(
            item: dict[str, Any],
        ):

            async with semaphore:

                raw = item["raw"]

                data = self._raw_to_dict(
                    raw,
                    item["keyword"],
                    item["provider"],
                )

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
                        f"Scraping failed: {exc}"
                    )

                    scraped = {}

                data["emails"] = (
                    scraped.get("emails")
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

                return data

        return list(
            await asyncio.gather(
                *[
                    enrich(item)
                    for item in results
                ],
                return_exceptions=False,
            )
        )

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

        sources = [
            LeadSource(
                provider=source["provider"],
                url=source.get("url"),
                matched_keyword=source.get(
                    "matched_keyword"
                ),
            )
            for source in source_entries
        ]

        score, reasons = self._rank(
            data=data,
            emails=emails,
            phones=phones,
            sources=sources,
        )

        has_contact = bool(
            emails or phones
        )

        # ---------------------------------------------------------
        # Lead validity is independent from ATREAL priority.
        #
        # Every legitimate discovered lead is retained.
        # The ATREAL score only tells us how strongly the lead
        # currently matches ATREAL's qualification criteria.
        # ---------------------------------------------------------

        quality_status = "valid"

        evidence = LeadEvidence(
            signals=reasons,
            source_count=len(sources),
            website_verified=bool(website),
            contact_verified=has_contact,
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
            country=data.get(
                "country"
            ),
            matched_keywords=matched_keywords,
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
            quality_status=quality_status,
            ranking_score=score,
            ranking_reasons=reasons,
            evidence=evidence,
        )

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
        Calculate the current ATREAL-specific lead score.

        Current scoring model:

            1. Real-estate developer fit      25
            2. MahaRERA evidence              25
            3. Construction timing            25
            4. Sales activity                 25

        MahaRERA, construction timing, and sales activity are
        intentionally zero until their respective enrichment
        layers are implemented.

        This method does NOT reject leads.
        It only assigns an ATREAL priority score.
        """

        score = 0.0
        reasons: list[str] = []

        name = (
            str(
                data.get(
                    "business_name",
                    "",
                )
            )
            .lower()
        )

        snippet = (
            str(
                data.get(
                    "snippet",
                    "",
                )
            )
            .lower()
        )

        text = f"{name} {snippet}"

        # =========================================================
        # 1. REAL-ESTATE DEVELOPER FIT — 25 POINTS
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
                "identified from discovery evidence."
            )

        # =========================================================
        # 2. MAHARERA EVIDENCE — 25 POINTS
        # =========================================================
        #
        # Reserved for the MahaRERA integration.
        #
        # We deliberately do not infer MahaRERA verification from
        # Google Maps or website data.
        # =========================================================

        # No points yet.

        # =========================================================
        # 3. CONSTRUCTION TIMING — 25 POINTS
        # =========================================================
        #
        # Reserved for project-stage enrichment.
        # =========================================================

        # No points yet.

        # =========================================================
        # 4. SALES ACTIVITY — 25 POINTS
        # =========================================================
        #
        # Reserved for project/sales evidence extraction.
        # =========================================================

        # No points yet.

        return (
            min(score, 100),
            reasons,
        )

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

            if key not in canonical:

                data = self._raw_to_dict(
                    raw,
                    item["keyword"],
                    item["provider"],
                )

                canonical[key] = data

                continue

            existing = canonical[key]

            if (
                item["keyword"]
                not in existing[
                    "matched_keywords"
                ]
            ):
                existing[
                    "matched_keywords"
                ].append(
                    item["keyword"]
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
                    item["keyword"]
                ),
            }

            if source not in existing[
                "sources"
            ]:
                existing[
                    "sources"
                ].append(source)

            self._merge_raw_fields(
                existing,
                raw,
            )

        return list(
            canonical.values()
        )

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
                pass

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
            return (
                f"place:{place_id}"
            )

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