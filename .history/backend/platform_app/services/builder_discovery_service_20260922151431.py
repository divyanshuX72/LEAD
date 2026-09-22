from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from platform_app.config.settings import get_settings
from platform_app.services.providers.google_maps import (
    GoogleMapsProvider,
)


@dataclass
class BuilderCandidate:
    name: str

    maps_url: str | None = None
    website: str | None = None
    domain: str | None = None

    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    rating: float | None = None
    review_count: int | None = None
    place_id: str | None = None

    keyword: str | None = None
    matched_keywords: set[str] = field(
        default_factory=set
    )

    qualification_status: str = "pending"
    qualification_reasons: list[str] = field(
        default_factory=list
    )

    evidence: list[dict] = field(
        default_factory=list
    )


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(value.split())


def normalize_name(value: str | None) -> str:
    value = normalize_text(value)

    suffixes = (
        " private limited",
        " pvt ltd",
        " pvt limited",
        " limited",
        " ltd",
        " llp",
        " realty",
        " developers",
        " developer",
        " builders",
        " builder",
        " constructions",
        " construction",
        " real estate",
    )

    changed = True

    while changed:
        changed = False

        for suffix in suffixes:
            if value.endswith(suffix):
                value = value[
                    : -len(suffix)
                ].strip()
                changed = True
                break

    return value


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""

    digits = "".join(
        character
        for character in value
        if character.isdigit()
    )

    if len(digits) > 10:
        digits = digits[-10:]

    return digits


def normalize_domain(value: str | None) -> str:
    if not value:
        return ""

    try:
        parsed = urlparse(value)

        host = (
            parsed.netloc
            or parsed.path
        ).lower()

        if host.startswith("www."):
            host = host[4:]

        return host.split(":")[0]

    except Exception:
        return ""


def normalize_address(value: str | None) -> str:
    return normalize_text(value)


INDIAN_STATES_AND_UTS = (
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "andaman and nicobar islands",
    "chandigarh",
    "dadra and nagar haveli and daman and diu",
    "delhi",
    "jammu and kashmir",
    "ladakh",
    "lakshadweep",
    "puducherry",
)


BUILDER_POSITIVE_TERMS = (
    "builder",
    "builders",
    "developer",
    "developers",
    "real estate developer",
    "property developer",
    "realty",
    "real estate",
    "construction",
    "constructions",
)


BUILDER_NEGATIVE_TERMS = (
    "real estate agent",
    "real estate agency",
    "property agent",
    "property broker",
    "real estate broker",
    "broker",
    "brokerage",
    "consultant",
    "consultancy",
    "architect",
    "architecture",
    "interior designer",
    "interior design",
    "property management",
)


def extract_postal_code(
    address: str | None,
) -> str | None:
    if not address:
        return None

    match = re.search(
        r"\b\d{6}\b",
        address,
    )

    return (
        match.group(0)
        if match
        else None
    )


def extract_geography(
    address: str | None,
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
]:
    if not address:
        return None, None, None, None

    parts = [
        part.strip()
        for part in address.split(",")
        if part.strip()
    ]

    normalized_parts = [
        normalize_text(part)
        for part in parts
    ]

    country = None
    state = None
    city = None

    for index in range(
        len(normalized_parts) - 1,
        -1,
        -1,
    ):
        part = normalized_parts[index]

        if part in {
            "india",
            "bharat",
        }:
            country = parts[index]
            break

    state_index = None

    for index, part in enumerate(
        normalized_parts
    ):
        if part in INDIAN_STATES_AND_UTS:
            state = parts[index]
            state_index = index
            break

    if state_index is not None:
        candidates = []

        for index in range(
            state_index - 1,
            -1,
            -1,
        ):
            value = normalized_parts[index]

            if re.fullmatch(
                r"\d{6}",
                value,
            ):
                continue

            if value in {
                "india",
                "bharat",
            }:
                continue

            if value in {
                "west",
                "east",
                "north",
                "south",
                "central",
            }:
                continue

            candidates.append(
                parts[index]
            )

        if candidates:
            city = candidates[0]

    postal_code = extract_postal_code(
        address
    )

    return (
        city,
        state,
        country,
        postal_code,
    )


def identity_score(
    candidate: BuilderCandidate,
    existing: BuilderCandidate,
) -> float:

    if (
        candidate.place_id
        and existing.place_id
        and candidate.place_id
        == existing.place_id
    ):
        return 1.0

    score = 0.0

    candidate_name = normalize_name(
        candidate.name
    )
    existing_name = normalize_name(
        existing.name
    )

    candidate_phone_set = {
        normalize_phone(phone)
        for phone in candidate.phones
        if normalize_phone(phone)
    }

    existing_phone_set = {
        normalize_phone(phone)
        for phone in existing.phones
        if normalize_phone(phone)
    }

    if (
        candidate_phone_set
        & existing_phone_set
    ):
        score += 0.40

    candidate_domain = normalize_domain(
        candidate.website
        or candidate.domain
    )

    existing_domain = normalize_domain(
        existing.website
        or existing.domain
    )

    if (
        candidate_domain
        and existing_domain
        and candidate_domain
        == existing_domain
    ):
        score += 0.35

    if (
        candidate_name
        and existing_name
        and candidate_name
        == existing_name
    ):
        score += 0.35

    candidate_address = normalize_address(
        candidate.address
    )

    existing_address = normalize_address(
        existing.address
    )

    if (
        candidate_address
        and existing_address
        and candidate_address
        == existing_address
    ):
        score += 0.20

    return score


def candidate_matches_run(
    candidate: BuilderCandidate,
    accepted: list[BuilderCandidate],
) -> bool:

    for existing in accepted:
        score = identity_score(
            candidate,
            existing,
        )

        if score >= 0.50:
            return True

    return False


class BuilderDiscoveryService:

    SEARCH_QUERIES = (
        "real estate developers",
        "builders",
        "property developers",
        "real estate builders",
        "realty developers",
        "residential builders",
    )

    def __init__(self):
        self.settings = get_settings()
        self.maps = GoogleMapsProvider()

    async def discover(
        self,
        *,
        workspace_id: str,
        location: str,
        target_limit: int,
    ) -> dict:

        if not await self.maps.is_available():
            raise RuntimeError(
                "Google Maps provider is not configured."
            )

        accepted: list[
            BuilderCandidate
        ] = []

        raw_results_count = 0
        duplicate_count = 0
        rejected_count = 0

        queries_used: list[str] = []

        exhausted = False

        for query in self.SEARCH_QUERIES:

            if len(accepted) >= target_limit:
                break

            page_token = None
            first_page = True

            while True:

                if len(accepted) >= target_limit:
                    break

                results, next_token = (
                    await self.maps.search(
                        query=query,
                        location=location,
                        limit=min(
                            self.settings
                            .MAX_SEARCH_RESULTS_PER_PROVIDER,
                            20,
                        ),
                        page_token=page_token,
                    )
                )

                if first_page:
                    queries_used.append(
                        query
                    )
                    first_page = False

                raw_results_count += len(
                    results
                )

                if not results:
                    break

                for raw in results:

                    if len(accepted) >= target_limit:
                        break

                    if not raw.title:
                        rejected_count += 1
                        continue

                    candidate = self._candidate_from_raw(
                        raw=raw,
                        keyword=query,
                    )

                    if candidate_matches_run(
                        candidate,
                        accepted,
                    ):
                        duplicate_count += 1
                        continue

                    await self._enrich_candidate(
                        candidate
                    )

                    qualification = (
                        self._qualify_candidate(
                            candidate
                        )
                    )

                    if not qualification:
                        candidate.qualification_status = (
                            "rejected"
                        )

                        rejected_count += 1
                        continue

                    candidate.qualification_status = (
                        "accepted"
                    )

                    accepted.append(candidate)

                if len(accepted) >= target_limit:
                    break

                if not next_token:
                    break

                page_token = next_token

            if len(accepted) >= target_limit:
                break

        if len(accepted) < target_limit:
            exhausted = True

        return {
            "success": True,
            "agent": (
                "atreal_lead_capture_agent"
            ),
            "discovery_type": "builder",
            "workspace_id": workspace_id,
            "location": location,
            "requested": target_limit,
            "returned": len(accepted),
            "raw_results": raw_results_count,
            "duplicates_removed": duplicate_count,
            "rejected": rejected_count,
            "discovery_exhausted": exhausted,
            "providers_used": [
                "google_maps"
            ],
            "queries_used": queries_used,
            "builders": [
                self._serialize_candidate(
                    candidate
                )
                for candidate in accepted
            ],
        }

    def _candidate_from_raw(
        self,
        *,
        raw,
        keyword: str,
    ) -> BuilderCandidate:

        website = getattr(
            raw,
            "website",
            None,
        )

        domain = getattr(
            raw,
            "domain",
            None,
        )

        if not domain:
            domain = normalize_domain(
                website
            )

        phone = getattr(
            raw,
            "phone",
            None,
        )

        city, state, country, postal_code = (
            extract_geography(
                getattr(
                    raw,
                    "address",
                    None,
                )
            )
        )

        candidate = BuilderCandidate(
            name=raw.title.strip(),
            maps_url=getattr(
                raw,
                "url",
                None,
            ),
            website=website,
            domain=domain or None,
            phones=(
                [phone]
                if phone
                else []
            ),
            address=getattr(
                raw,
                "address",
                None,
            ),
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            rating=getattr(
                raw,
                "rating",
                None,
            ),
            review_count=getattr(
                raw,
                "review_count",
                None,
            ),
            place_id=getattr(
                raw,
                "place_id",
                None,
            ),
            keyword=keyword,
        )

        candidate.matched_keywords.add(
            keyword
        )

        candidate.evidence.append(
            {
                "source_type": "google_maps",
                "source_url": candidate.maps_url,
                "field": "business_identity",
                "value": candidate.name,
                "reason": (
                    "Business discovered "
                    "through Google Maps."
                ),
            }
        )

        if candidate.website:
            candidate.evidence.append(
                {
                    "source_type": "google_maps",
                    "source_url": candidate.maps_url,
                    "field": "website",
                    "value": candidate.website,
                    "reason": (
                        "Website supplied by "
                        "Google Maps."
                    ),
                }
            )

        if candidate.address:
            candidate.evidence.append(
                {
                    "source_type": "google_maps",
                    "source_url": candidate.maps_url,
                    "field": "address",
                    "value": candidate.address,
                    "reason": (
                        "Business address supplied "
                        "by Google Maps."
                    ),
                }
            )

        if candidate.phone:
            candidate.evidence.append(
                {
                    "source_type": "google_maps",
                    "source_url": candidate.maps_url,
                    "field": "phone",
                    "value": candidate.phone,
                    "reason": (
                        "Business phone supplied "
                        "by Google Maps."
                    ),
                }
            )

        return candidate

    async def _enrich_candidate(
        self,
        candidate: BuilderCandidate,
    ) -> None:

        if not candidate.website:
            return

        try:
            timeout = httpx.Timeout(
                self.settings
                .SCRAPE_TIMEOUT_SECONDS
            )

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; "
                    "ATREAL-BuilderDiscovery/1.0)"
                )
            }

            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:

                response = await client.get(
                    candidate.website
                )

                response.raise_for_status()

                content_type = (
                    response.headers
                    .get(
                        "content-type",
                        "",
                    )
                    .lower()
                )

                if "html" not in content_type:
                    return

                html = response.text

        except Exception as exc:

            candidate.evidence.append(
                {
                    "source_type": "website",
                    "source_url": candidate.website,
                    "field": "enrichment",
                    "value": None,
                    "reason": (
                        "Website enrichment failed: "
                        f"{type(exc).__name__}"
                    ),
                }
            )

            return

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        text = soup.get_text(
            " ",
            strip=True,
        )

        normalized_text = normalize_text(
            text
        )

        self._extract_emails(
            html,
            candidate,
        )

        self._extract_phones(
            text,
            candidate,
        )

        identity_name = normalize_name(
            candidate.name
        )

        identity_tokens = [
            token
            for token in identity_name.split()
            if len(token) >= 3
        ]

        matched_identity_tokens = [
            token
            for token in identity_tokens
            if token in normalized_text
        ]

        if matched_identity_tokens:
            candidate.evidence.append(
                {
                    "source_type": "website",
                    "source_url": candidate.website,
                    "field": "company_identity",
                    "value": candidate.name,
                    "reason": (
                        "Website contains company "
                        "identity terms."
                    ),
                }
            )

        positive_terms = [
            term
            for term in BUILDER_POSITIVE_TERMS
            if normalize_text(term)
            in normalized_text
        ]

        if positive_terms:
            candidate.evidence.append(
                {
                    "source_type": "website",
                    "source_url": candidate.website,
                    "field": "builder_activity",
                    "value": ", ".join(
                        positive_terms
                    ),
                    "reason": (
                        "Website contains terms "
                        "associated with builder/"
                        "developer activity."
                    ),
                }
            )

        candidate.city, candidate.state, candidate.country, candidate.postal_code = (
            extract_geography(
                candidate.address
            )
        )

    @staticmethod
    def _extract_emails(
        html: str,
        candidate: BuilderCandidate,
    ) -> None:

        matches = re.findall(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            html,
            flags=re.IGNORECASE,
        )

        for email in matches:

            email = email.lower().strip()

            if email not in candidate.emails:
                candidate.emails.append(
                    email
                )

                candidate.evidence.append(
                    {
                        "source_type": "website",
                        "source_url": candidate.website,
                        "field": "email",
                        "value": email,
                        "reason": (
                            "Public email address "
                            "found on company website."
                        ),
                    }
                )

        @staticmethod
    def _extract_phones(
        text: str,
        candidate: BuilderCandidate,
    ) -> None:

        matches = re.findall(
            r"(?:\+91[\s-]?)?[6-9]\d{9}",
            text,
        )

        for phone in matches:
            normalized = normalize_phone(phone)

            if not normalized:
                continue

            if any(
                normalize_phone(existing)
                == normalized
                for existing in candidate.phones
            ):
                continue

            clean_phone = phone.strip()

            candidate.phones.append(
                clean_phone
            )

            candidate.evidence.append(
                {
                    "source_type": "website",
                    "source_url": candidate.website,
                    "field": "phone",
                    "value": clean_phone,
                    "reason": (
                        "Public phone number "
                        "found on company website."
                    ),
                }
            )

    @staticmethod
    def _qualify_candidate(
        candidate: BuilderCandidate,
    ) -> bool:

        name_text = normalize_text(
            candidate.name
        )

        website_evidence = " ".join(
            str(
                evidence.get(
                    "value"
                )
                or ""
            )
            for evidence in candidate.evidence
            if evidence.get(
                "source_type"
            )
            == "website"
        )

        combined = (
            f"{name_text} "
            f"{normalize_text(website_evidence)}"
        )

        positive_matches = [
            term
            for term in BUILDER_POSITIVE_TERMS
            if normalize_text(term)
            in combined
        ]

        negative_matches = [
            term
            for term in BUILDER_NEGATIVE_TERMS
            if normalize_text(term)
            in combined
        ]

        if positive_matches:
            candidate.qualification_reasons.append(
                "Builder/developer terminology "
                f"found: {', '.join(positive_matches)}."
            )

            return True

        if negative_matches:
            candidate.qualification_reasons.append(
                "Candidate appears to be a "
                f"non-builder service: "
                f"{', '.join(negative_matches)}."
            )

            return False

        candidate.qualification_reasons.append(
            "No sufficient builder/developer "
            "evidence found."
        )

        return False

    @staticmethod
    def _serialize_candidate(
        candidate: BuilderCandidate,
    ) -> dict:

        return {
            "business_name": candidate.name,
            "domain": candidate.domain,
            "website": candidate.website,
            "phones": candidate.phones,
            "emails": candidate.emails,
            "address": candidate.address,
            "city": candidate.city,
            "state": candidate.state,
            "country": candidate.country,
            "postal_code": candidate.postal_code,
            "place_id": candidate.place_id,
            "maps_url": candidate.maps_url,
            "rating": candidate.rating,
            "review_count": candidate.review_count,
            "qualification_status": (
                candidate.qualification_status
            ),
            "qualification_reasons": (
                candidate.qualification_reasons
            ),
            "matched_keyword": candidate.keyword,
            "matched_keywords": sorted(
                candidate.matched_keywords
            ),
            "provider": "google_maps",
            "evidence": candidate.evidence,
        }