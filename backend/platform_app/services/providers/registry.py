from platform_app.services.providers.base import SearchProvider
from platform_app.services.providers.brave import BraveProvider
from platform_app.services.providers.google_maps import GoogleMapsProvider
from platform_app.services.providers.serper import SerperProvider
from platform_app.services.providers.tavily import TavilyProvider


ALL_PROVIDERS = [
    SerperProvider,
    GoogleMapsProvider,
    TavilyProvider,
    BraveProvider,
]


class ProviderRegistry:
    """
    Registry of reliable API-backed lead discovery providers.

    DuckDuckGo is intentionally excluded because its HTML endpoint
    currently responds with an anti-bot challenge rather than
    dependable search results.
    """

    def __init__(self):
        self._providers: dict[str, SearchProvider] = {}

        for provider_class in ALL_PROVIDERS:
            provider = provider_class()
            self._providers[provider.name] = provider

    async def get_available_providers(
        self,
    ) -> list[SearchProvider]:

        available: list[SearchProvider] = []

        for provider in self._providers.values():
            try:
                if await provider.is_available():
                    available.append(provider)
            except Exception as exc:
                print(
                    f"[ProviderRegistry] "
                    f"{provider.name} unavailable: {exc}"
                )

        return available

    async def get_primary_provider(
        self,
    ) -> SearchProvider | None:

        providers = await self.get_available_providers()

        if not providers:
            return None

        return providers[0]

    def get_provider(
        self,
        name: str,
    ) -> SearchProvider | None:

        return self._providers.get(name)
