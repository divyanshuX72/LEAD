"""
Tavily Search Provider

AI-optimized search API.
"""

import httpx
import tldextract

from platform_app.services.providers.base import SearchProvider, RawSearchResult
from platform_app.config.settings import get_settings


class TavilyProvider(SearchProvider):
    name = "tavily"
    
    def __init__(self):
        self.settings = get_settings()
        
    async def is_available(self) -> bool:
        return bool(self.settings.TAVILY_API_KEY)
        
    async def search(self, query: str, location: str | None = None, limit: int = 10, page: int = 1, page_token: str | None = None) -> tuple[list[RawSearchResult], str | None]:
        if not await self.is_available() or page > 1:
            return [], None
            
        search_term = query
        if location:
            search_term = f"{query} in {location}"
            
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.TAVILY_API_KEY,
            "query": search_term,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": limit
        }
        
        results: list[RawSearchResult] = []
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("results", []):
                    link = item.get("url")
                    if not link:
                        continue
                        
                    ext = tldextract.extract(link)
                    domain = f"{ext.domain}.{ext.suffix}"
                    
                    results.append(RawSearchResult(
                        title=item.get("title"),
                        url=link,
                        snippet=item.get("content"),
                        domain=domain
                    ))
                    
            except Exception as e:
                print(f"Tavily search failed: {e}")
                
        return results, None
