"""
DuckDuckGo Search Provider

Requires no API key. Scrapes DuckDuckGo HTML results (lite version).
Used as a fallback when no API keys are provided.
"""

import httpx
from bs4 import BeautifulSoup, Tag
import tldextract
from urllib.parse import unquote

from platform_app.services.providers.base import SearchProvider, RawSearchResult


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"
    
    async def is_available(self) -> bool:
        return True  # Always available, no API key needed
        
    async def search(self, query: str, location: str | None = None, limit: int = 10, page: int = 1, page_token: str | None = None) -> tuple[list[RawSearchResult], str | None]:
        if page > 3:
            return [], None
            
        search_term = query
        if location:
            search_term = f"{query} in {location}"
            
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        data = {"q": search_term}
        # DuckDuckGo uses 's' (offset) for pagination
        if page > 1:
            data["s"] = str((page - 1) * 30)
            data["dc"] = str((page - 1) * 30 + 1)
        
        results: list[RawSearchResult] = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, data=data, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                for a in soup.find_all("a", class_="result__url"):
                    if not isinstance(a, Tag):
                        continue
                    if len(results) >= limit:
                        break
                        
                    href = str(a.get("href", ""))
                    if not href:
                        continue
                        
                    # Extract original URL from DDG redirect
                    if "uddg=" in href:
                        try:
                            actual_url = unquote(href.split("uddg=")[1].split("&")[0])
                        except IndexError:
                            actual_url = href
                    else:
                        actual_url = href
                        
                    # Extract domain
                    ext = tldextract.extract(actual_url)
                    domain = f"{ext.domain}.{ext.suffix}"
                    
                    if not domain or domain.startswith("."):
                        continue
                        
                    # Get snippet and title
                    parent = a.find_parent("div", class_="result")
                    title = ""
                    snippet = ""
                    
                    if isinstance(parent, Tag):
                        title_el = parent.find("h2", class_="result__title")
                        if isinstance(title_el, Tag):
                            title = title_el.get_text(strip=True)
                            
                        snippet_el = parent.find("a", class_="result__snippet")
                        if isinstance(snippet_el, Tag):
                            snippet = snippet_el.get_text(strip=True)
                            
                    results.append(RawSearchResult(
                        title=title,
                        url=actual_url,
                        snippet=snippet,
                        domain=domain
                    ))
                    
            except Exception as e:
                print(f"DuckDuckGo search failed: {e}")
                
        return results, None
