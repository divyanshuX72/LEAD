"""
Search Providers Base Protocol

Defines the interface that all search providers must implement.
"""

from typing import Protocol, Any
from pydantic import BaseModel


class RawSearchResult(BaseModel):
    """Normalized search result returned by any provider."""
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    domain: str | None = None
    
    # Specific to map/business providers
    phone: str | None = None
    address: str | None = None
    rating: float | None = None
    place_id: str | None = None


class SearchProvider(Protocol):
    """Protocol for all search providers."""
    
    name: str
    
    async def is_available(self) -> bool:
        """Check if the provider is configured and available to use (e.g., API key present)."""
        ...
        
    async def search(self, query: str, location: str | None = None, limit: int = 10, page: int = 1, page_token: str | None = None) -> tuple[list[RawSearchResult], str | None]:
        """Execute a search query and return (results, next_page_token). page starts at 1."""
        ...
