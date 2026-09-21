"""
Brave Search Provider
"""

import httpx
import tldextract

from platform_app.services.providers.base import SearchProvider, RawSearchResult
from platform_app.config.settings import get_settings


class BraveProvider(SearchProvider):
    name = "brave"
    
    def __init__(self):
        self.settings = get_settings()
        
    async def is_available(self) -> bool:
        return bool(self.settings.BRAVE_API_KEY)
        
    async def search(self, query: str, location: str | None = None, limit: int = 10, page: int = 1, page_token: str | None = None) -> tuple[list[RawSearchResult], str | None]:
        if not await self.is_available():
            return [], None
            
        search_term = query
        if location:
            search_term = f"{query} in {location}"
            
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.settings.BRAVE_API_KEY or ""
        }
        params = {
            "q": search_term,
            "count": min(limit, 20),  # Max 20
            "offset": (page - 1) * min(limit, 20)
        }
        
        results: list[RawSearchResult] = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                web_results = data.get("web", {}).get("results", [])
                
                for item in web_results:
                    if len(results) >= limit:
                        break
                        
                    link = item.get("url")
                    if not link:
                        continue
                        
                    ext = tldextract.extract(link)
                    domain = f"{ext.domain}.{ext.suffix}"
                    
                    results.append(RawSearchResult(
                        title=item.get("title"),
                        url=link,
                        snippet=item.get("description"),
                        domain=domain
                    ))
                    
            except Exception as e:
                print(f"Brave search failed: {e}")
                
        return results, None


