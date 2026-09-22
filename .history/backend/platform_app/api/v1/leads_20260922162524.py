from fastapi import APIRouter, HTTPException

from platform_app.schemas.builder_discovery import (
    BuilderDiscoveryRequest,
    BuilderDiscoveryResponse,
)
from platform_app.services.builder_discovery_service import (
    BuilderDiscoveryService,
)


router = APIRouter(
    prefix="/leads",
    tags=["Lead Capture"],
)


@router.post(
    "/builder-discovery",
    response_model=BuilderDiscoveryResponse,
)
async def discover_builders(
    request: BuilderDiscoveryRequest,
):
    service = BuilderDiscoveryService()

    try:
        return await service.discover(
            workspace_id=request.workspace_id,
            location=request.location,
            target_limit=request.target_limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(
            f"[BuilderDiscovery API] Discovery failed: {exc}"
        )
        raise HTTPException(
            status_code=500,
            detail="Builder discovery failed.",
        ) from exc