import sys
import asyncio

sys.path.insert(0, "backend")

from platform_app.services.providers.registry import ProviderRegistry
from platform_app.services.lead_capture_service import LeadCaptureService


async def main():
    registry = ProviderRegistry()

    available = await registry.get_available_providers()

    print("REGISTRY AVAILABLE:", [p.name for p in available])

    service = LeadCaptureService()

    print("SERVICE TYPE:", type(service).__name__)
    print("SERVICE ATTRIBUTES:")

    for name, value in vars(service).items():
        print(f"  {name}: {type(value).__name__}")

    if hasattr(service, "provider_registry"):
        registry2 = service.provider_registry
        print(
            "SERVICE REGISTRY AVAILABLE:",
            [p.name for p in await registry2.get_available_providers()],
        )

    if hasattr(service, "registry"):
        registry3 = service.registry
        print(
            "SERVICE registry AVAILABLE:",
            [p.name for p in await registry3.get_available_providers()],
        )

    if hasattr(service, "provider"):
        print("SERVICE PROVIDER:", getattr(service.provider, "name", None))


if __name__ == "__main__":
    asyncio.run(main())
