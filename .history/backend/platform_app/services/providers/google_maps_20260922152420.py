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
        