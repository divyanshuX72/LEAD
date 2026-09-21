from fastapi import APIRouter, HTTPException

from platform_app.schemas.lead import (
    LeadSearchRequest,
    LeadSearchResponse,
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
    """
    Discover ATREAL-qualified real-estate developer leads.

    This endpoint is stateless.

    No batch is created.
    No database record is created.
    No authentication is required.
    """

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