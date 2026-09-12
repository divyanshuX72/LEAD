"""
Serper.dev Search Provider

Google Search API using serper.dev
"""

import httpx
import tldextract

from platform_app.services.providers.base import SearchProvider, RawSearchResult
from platform_app.config.settings import get_settings


class SerperProvider(SearchProvider):
    name = "serper"
    
    def __init__(self):
        self.settings = get_settings()
        
    async def is_available(self) -> bool:
        return bool(self.settings.SERPER_API_KEY)
        
    async def search(self, query: str, location: str | None = None, limit: int = 10, page: int = 1, page_token: str | None = None) -> tuple[list[RawSearchResult], str | None]:
        if not await self.is_available():
            return [], None
            
        search_term = query
        if location:
            search_term = f"{query} in {location}"
            
        url = "https://google.serper.dev/search"
        payload = {
            "q": search_term,
            "num": limit,
            "page": page
        }
        
        api_key = self.settings.SERPER_API_KEY
        if not api_key:
            return [], None
            
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        results: list[RawSearchResult] = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Try organic results first
                organic = data.get("organic", [])
                
                for item in organic:
                    if len(results) >= limit:
                        break
                        
                    link = item.get("link")
                    if not link:
                        continue
                        
                    ext = tldextract.extract(link)
                    domain = f"{ext.domain}.{ext.suffix}"
                    
                    results.append(RawSearchResult(
                        title=item.get("title"),
                        url=link,
                        snippet=item.get("snippet"),
                        domain=domain
                    ))
                    
            except Exception as e:
                print(f"Serper search failed: {e}")
                
        return results, None
