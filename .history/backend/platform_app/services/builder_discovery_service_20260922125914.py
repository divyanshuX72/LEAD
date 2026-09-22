from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from platform_app.config.settings import get_settings
from platform_app.services.data_service import (
    DataServiceClient,
)
from platform_app.services.providers.google_maps import (
    GoogleMapsProvider,
)


@dataclass
class BuilderCandidate:
    name: str
    maps_url: str | None
    website: str | None
    phone: str | None
    address: str | None
    rating: float | None
    review_count: int | None
    place_id: str | None
    keyword: str


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()

    for character in (
        ".",
        ",",
        "-",
        "_",
        "/",
        "\\",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        "&",
    ):
        value = value.replace(character, " ")

    return " ".join(value.split())


def normalize_name(value: str | None) -> str:
    value = normalize_text(value)

    suffixes = (
        " private limited",
        " pvt ltd",
        " pvt. ltd",
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
                    :-len(suffix)
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


def candidate_matches_identity(
    candidate: BuilderCandidate,
    existing: dict,
) -> bool:

    candidate_place_id = candidate.place_id
    existing_place_id = existing.get("place_id")

    if (
        candidate_place_id
        and existing_place_id
        and candidate_place_id == existing_place_id
    ):
        return True

    candidate_domain = normalize_domain(
        candidate.website
    )

    existing_domain = normalize_domain(
        existing.get("website")
        or existing.get("domain")
    )

    if (
        candidate_domain
        and existing_domain
        and candidate_domain == existing_domain
    ):
        return True

    candidate_phone = normalize_phone(
        candidate.phone
    )

    existing_phones = existing.get(
        "phones",
        [],
    )

    if isinstance(existing_phones, str):
        existing_phones = [existing_phones]

    for phone in existing_phones:
        if (
            candidate_phone
            and normalize_phone(phone)
            and candidate_phone
            == normalize_phone(phone)
        ):
            return True

    candidate_name = normalize_name(
        candidate.name
    )

    existing_name = normalize_name(
        existing.get("name")
        or existing.get("business_name")
    )

    if (
        candidate_name
        and existing_name
        and candidate_name == existing_name
    ):
        return True

    candidate_address = normalize_address(
        candidate.address
    )

    existing_address = normalize_address(
        existing.get("address")
    )

    if (
        candidate_name
        and existing_name
        and candidate_name == existing_name
        and candidate_address
        and existing_address
        and candidate_address == existing_address
    ):
        return True

    return False


def candidate_matches_run(
    candidate: BuilderCandidate,
    accepted: list[BuilderCandidate],
) -> bool:

    candidate_place_id = candidate.place_id

    if candidate_place_id:
        for existing in accepted:
            if (
                existing.place_id
                and existing.place_id
                == candidate_place_id
            ):
                return True

    candidate_domain = normalize_domain(
        candidate.website
    )

    candidate_phone = normalize_phone(
        candidate.phone
    )

    candidate_name = normalize_name(
        candidate.name
    )

    for existing in accepted:

        existing_domain = normalize_domain(
            existing.website
        )

        existing_phone = normalize_phone(
            existing.phone
        )

        existing_name = normalize_name(
            existing.name
        )

        if (
            candidate_domain
            and existing_domain
            and candidate_domain
            == existing_domain
        ):
            return True

        if (
            candidate_phone
            and existing_phone
            and candidate_phone
            == existing_phone
        ):
            return True

        if (
            candidate_name
            and existing_name
            and candidate_name
            == existing_name
        ):
            return True

    return False


class BuilderDiscoveryService:

    SEARCH_QUERIES = (
        "real estate developers",
        "builders",
        "property developers",
        "real estate builders",
    )

    def __init__(self):
        settings = get_settings()

        self.settings = settings

        self.maps = GoogleMapsProvider()

        self.data_service = DataServiceClient(
            base_url=settings.DATA_SERVICE_URL,
            timeout=settings.DATA_SERVICE_TIMEOUT_SECONDS,
        )

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

        # -------------------------------------------------
        # 1. Load builders already known by ATREAL
        # -------------------------------------------------

        existing_builders = (
            await self.data_service.get_known_builders(
                workspace_id
            )
        )

        # -------------------------------------------------
        # 2. Create discovery batch
        # -------------------------------------------------

        batch = await self.data_service.create_batch(
            workspace_id=workspace_id,
            location=location,
            target_limit=target_limit,
            keywords=list(self.SEARCH_QUERIES),
        )

        batch_id = batch["batch_id"]

        accepted: list[BuilderCandidate] = []

        raw_results_count = 0
        duplicate_count = 0
        rejected_count = 0

        page_tokens: dict[
            str,
            str | None
        ] = {
            query: None
            for query in self.SEARCH_QUERIES
        }

        exhausted = False

        try:

            # -------------------------------------------------
            # 3. Search until target unique builders reached
            # -------------------------------------------------

            while len(accepted) < target_limit:

                made_progress = False
                token_available = False

                for query in self.SEARCH_QUERIES:

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
                            page_token=page_tokens[
                                query
                            ],
                        )
                    )

                    page_tokens[query] = next_token

                    if next_token:
                        token_available = True

                    raw_results_count += len(results)

                    for raw in results:

                        if len(accepted) >= target_limit:
                            break

                        if not raw.title:
                            rejected_count += 1
                            continue

                        made_progress = True

                        candidate = BuilderCandidate(
                            name=raw.title.strip(),
                            maps_url=raw.url,
                            website=raw.website,
                            phone=raw.phone,
                            address=raw.address,
                            rating=raw.rating,
                            review_count=raw.review_count,
                            place_id=raw.place_id,
                            keyword=query,
                        )

                        # -------------------------------------
                        # Existing builder
                        # -------------------------------------

                        if any(
                            candidate_matches_identity(
                                candidate,
                                existing,
                            )
                            for existing
                            in existing_builders
                        ):
                            duplicate_count += 1
                            continue

                        # -------------------------------------
                        # Duplicate in current discovery run
                        # -------------------------------------

                        if candidate_matches_run(
                            candidate,
                            accepted,
                        ):
                            duplicate_count += 1
                            continue

                        accepted.append(candidate)

                # -------------------------------------------------
                # No more provider pages
                # -------------------------------------------------

                if len(accepted) >= target_limit:
                    break

                if not token_available:
                    exhausted = True
                    break

                if not made_progress:
                    exhausted = True
                    break

            # -------------------------------------------------
            # 4. Persist accepted builders
            # -------------------------------------------------

            persisted_builders = []

            for candidate in accepted:

                lead_response = (
                    await self.data_service.create_lead(
                        {
                            "workspace_id": workspace_id,
                            "business_name": candidate.name,
                            "emails": [],
                            "phones": (
                                [candidate.phone]
                                if candidate.phone
                                else []
                            ),
                            "website": candidate.website,
                            "address": candidate.address,
                            "city": None,
                            "state": None,
                            "country": "India",
                            "industry": (
                                "Real Estate Developer"
                            ),
                            "matched_keyword": (
                                candidate.keyword
                            ),
                            "source_primary": (
                                "google_maps"
                            ),
                            "source_url": (
                                candidate.maps_url
                            ),
                            "rating": candidate.rating,
                            "review_count": (
                                candidate.review_count
                            ),
                            "quality_status": "valid",
                        }
                    )
                )

                await self.data_service.add_batch_result(
                    batch_id=batch_id,
                    lead_id=lead_response["lead_id"],
                    matched_keyword=candidate.keyword,
                    provider="google_maps",
                    provider_identifier=candidate.place_id,
                )

                persisted_builders.append(
                    {
                        "business_name": candidate.name,
                        "website": candidate.website,
                        "phone": candidate.phone,
                        "address": candidate.address,
                        "rating": candidate.rating,
                        "review_count": (
                            candidate.review_count
                        ),
                        "place_id": candidate.place_id,
                        "maps_url": candidate.maps_url,
                        "matched_keyword": candidate.keyword,
                        "lead_id": (
                            lead_response["lead_id"]
                        ),
                        "company_id": (
                            lead_response["company_id"]
                        ),
                        "contact_id": (
                            lead_response["contact_id"]
                        ),
                    }
                )

            # -------------------------------------------------
            # 5. Complete batch
            # -------------------------------------------------

            await self.data_service.update_batch(
                batch_id=batch_id,
                status="completed",
                raw_results_count=raw_results_count,
                final_count=len(accepted),
                duplicate_count=duplicate_count,
                rejected_count=rejected_count,
                completed=True,
            )

            return {
                "success": True,
                "agent": (
                    "atreal_lead_capture_agent"
                ),
                "discovery_type": "builder",
                "workspace_id": workspace_id,
                "location": location,
                "requested": target_limit,
                "returned": len(
                    persisted_builders
                ),
                "raw_results": raw_results_count,
                "duplicates_removed": (
                    duplicate_count
                ),
                "rejected": rejected_count,
                "discovery_exhausted": exhausted,
                "batch_id": batch_id,
                "builders": persisted_builders,
            }

        except Exception:

            await self.data_service.update_batch(
                batch_id=batch_id,
                status="failed",
                raw_results_count=raw_results_count,
                final_count=len(accepted),
                duplicate_count=duplicate_count,
                rejected_count=rejected_count,
                completed=False,
            )

            raise