import sys
import asyncio

sys.path.insert(0, "backend")

from platform_app.config.settings import get_settings
from platform_app.services.providers.registry import ProviderRegistry


async def main():
    settings = get_settings()

    print("SETTINGS KEY:", bool(settings.GOOGLE_MAPS_API_KEY))

    registry = ProviderRegistry()

    print("REGISTERED PROVIDERS:", list(registry._providers.keys()))

    for name, provider in registry._providers.items():
        try:
            available = await provider.is_available()
            print(f"{name}: available={available}")
        except Exception as exc:
            print(f"{name}: ERROR={type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
