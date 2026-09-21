"""
Provider Registry

Discovers and provides access to configured search providers.
"""

from platform_app.services.providers.base import SearchProvider
from platform_app.services.providers.serper import SerperProvider
from platform_app.services.providers.tavily import TavilyProvider
from platform_app.services.providers.google_maps import GoogleMapsProvider
from platform_app.services.providers.brave import BraveProvider
from platform_app.services.providers.duckduckgo import DuckDuckGoProvider

# All available providers in preferred order
ALL_PROVIDERS = [
    SerperProvider,
    TavilyProvider,
    GoogleMapsProvider,
    BraveProvider,
    DuckDuckGoProvider
]


class ProviderRegistry:
    """Registry to manage and fetch search providers."""
    
    def __init__(self):
        self._providers: dict[str, SearchProvider] = {}
        # Instantiate all providers
        for provider_class in ALL_PROVIDERS:
            provider = provider_class()
            self._providers[provider.name] = provider
            
    async def get_available_providers(self) -> list[SearchProvider]:
        """Get all providers that are correctly configured and available."""
        available = []
        for provider in self._providers.values():
            if await provider.is_available():
                available.append(provider)
        return available
        
    async def get_primary_provider(self) -> SearchProvider | None:
        """Get the most preferred available provider."""
        available = await self.get_available_providers()
        return available[0] if available else None
        
    def get_provider(self, name: str) -> SearchProvider | None:
        """Get a specific provider by name."""
        return self._providers.get(name)
