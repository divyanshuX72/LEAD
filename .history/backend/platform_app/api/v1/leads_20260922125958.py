from fastapi import APIRouter, HTTPException

from platform_app.schemas.lead import (
    BuilderDiscoveryRequest,
    BuilderDiscoveryResponse,
    LeadSearchRequest,
    LeadSearchResponse,
)
from platform_app.services.builder_discovery_service import (
    BuilderDiscoveryService,
)
from platform_app.services.lead_capture_service import (
    LeadCaptureService,
)


router = APIRouter(
    prefix="/leads",
    tags=["Lead Capture"],
)


@router.post(
    "/search",
    response_model=LeadSearchResponse,
)
async def discover_leads(
    request: LeadSearchRequest,
):
    service = LeadCaptureService()

    try:
        return await service.discover(
            keywords=request.keywords,
            location=request.location,
            limit=request.limit,
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
            f"[LeadCapture API] "
            f"Discovery failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Lead discovery failed.",
        ) from exc


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
            f"[BuilderDiscovery API] "
            f"Discovery failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Builder discovery failed.",
        ) from exc