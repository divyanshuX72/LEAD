from __future__ import annotations

from urllib.parse import quote_plus

import httpx

from platform_app.config.settings import get_settings
from platform_app.services.providers.base import RawSearchResult


class GoogleMapsProvider:
    name = "google_maps"

    SEARCH_URL = (
        "https://places.googleapis.com/v1/places:searchText"
    )

    def __init__(self):
        self.settings = get_settings()

    async def is_available(self) -> bool:
        return bool(self.settings.GOOGLE_MAPS_API_KEY)

    async def search(
        self,
        query,
        location=None,
        limit=10,
        page=1,
    page_token=None,
):
    if not self.settings.GOOGLE_MAPS_API_KEY:
        return [], None

    text_query = query

    if location:
        text_query = f"{query} in {location}"

    payload = {
        "textQuery": text_query,
        "pageSize": min(limit, 20),
    }

    if page_token:
        payload["pageToken"] = page_token

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": self.settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.nationalPhoneNumber,"
            "places.websiteUri,"
            "places.rating,"
            "places.userRatingCount,"
            "places.googleMapsUri,"
            "nextPageToken"
        ),
    }

    timeout = httpx.Timeout(
        self.settings.SEARCH_TIMEOUT_SECONDS
    )

    print(
        "[GoogleMaps] POST",
        self.SEARCH_URL,
        "query=",
        text_query,
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(
                self.SEARCH_URL,
                json=payload,
                headers=headers,
            )

    except Exception as exc:
        print(
            "[GoogleMaps] HTTP request failed:",
            type(exc).__name__,
            str(exc),
        )
        raise

    print(
        "[GoogleMaps] response:",
        response.status_code,
    )

    if response.status_code >= 400:
        print(
            "[GoogleMaps] response body:",
            response.text[:2000],
        )

    response.raise_for_status()

    data = response.json()

    results = []

    for place in data.get("places", []):
        display_name = (
            place.get("displayName")
            or {}
        )

        name = display_name.get("text")

        maps_url = place.get(
            "googleMapsUri"
        )

        website = place.get(
            "websiteUri"
        )

        domain = None

        if website:
            try:
                parsed = urlparse(
                    website
                )

                domain = (
                    parsed.netloc
                    .lower()
                )

                if domain.startswith("www."):
                    domain = domain[4:]

                domain = domain.split(":")[0]

            except Exception:
                domain = None

        results.append(
            RawSearchResult(
                title=name,
                url=maps_url,
                website=website,
                domain=domain,
                phone=place.get(
                    "nationalPhoneNumber"
                ),
                address=place.get(
                    "formattedAddress"
                ),
                rating=place.get(
                    "rating"
                ),
                review_count=place.get(
                    "userRatingCount"
                ),
                place_id=place.get("id"),
            )
        )

    return (
        results,
        data.get("nextPageToken"),
    )