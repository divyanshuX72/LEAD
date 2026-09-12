"""
Google Maps Search Provider

Uses Google Places API for business listings.
"""

import httpx
import tldextract
from urllib.parse import quote

from platform_app.services.providers.base import SearchProvider, RawSearchResult
from platform_app.config.settings import get_settings


class GoogleMapsProvider(SearchProvider):
    name = "google_maps"
    
    def __init__(self):
        self.settings = get_settings()
        
    async def is_available(self) -> bool:
        return bool(self.settings.GOOGLE_MAPS_API_KEY)
        
    async def search(self, query: str, location: str | None = None, limit: int = 10, page: int = 1, page_token: str | None = None) -> tuple[list[RawSearchResult], str | None]:
        if not await self.is_available():
            return [], None
            
        search_term = query
        if location:
            search_term = f"{query} in {location}"
            
        # Text Search (New) API
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "X-Goog-Api-Key": self.settings.GOOGLE_MAPS_API_KEY or "",
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.rating,places.id,nextPageToken",
            "Content-Type": "application/json"
        }
        
        # Max results per page is 20 for this API
        actual_limit = min(limit, 20)
        
        payload = {
            "textQuery": search_term,
            "pageSize": actual_limit
        }
        if page_token:
            payload["pageToken"] = page_token
            
        results: list[RawSearchResult] = []
        next_page_token = None
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                places = data.get("places", [])
                next_page_token = data.get("nextPageToken")
                
                for place in places:
                    link = place.get("websiteUri")
                    domain = None
                    if link:
                        ext = tldextract.extract(link)
                        domain = f"{ext.domain}.{ext.suffix}"
                        
                    display_name = place.get("displayName", {}).get("text", "")
                        
                    results.append(RawSearchResult(
                        title=display_name,
                        url=link,
                        domain=domain,
                        phone=place.get("nationalPhoneNumber"),
                        address=place.get("formattedAddress"),
                        rating=place.get("rating"),
                        place_id=place.get("id")
                    ))
                    
            except Exception as e:
                print(f"Google Maps search failed: {e}")
                
        return results, next_page_token
