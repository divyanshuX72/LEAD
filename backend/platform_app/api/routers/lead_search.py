"""
Lead Search API Router — Lead Agent (Multi-Tenant)

POST /api/v1/leads/search — Start a lead discovery session (company-scoped)
"""

from fastapi import APIRouter, Depends, BackgroundTasks

from platform_app.core.auth import get_current_user
from platform_app.models.user import User
from platform_app.schemas.lead import LeadSearchRequest, LeadBatchResponse
from platform_app.services.lead_discovery_orchestrator import LeadDiscoveryOrchestrator
from platform_app.api.dependencies import get_lead_orchestrator
from platform_app.models.lead_batch import LeadBatch
from sqlalchemy import select

router = APIRouter(prefix="/leads", tags=["Lead Search"])


@router.post("/search", response_model=dict)
async def start_lead_search(
    request: LeadSearchRequest,
    background_tasks: BackgroundTasks,
    orchestrator: LeadDiscoveryOrchestrator = Depends(get_lead_orchestrator),
):
    """Start a lead discovery session with multiple keywords.
    
    The search runs in the background and emits Socket.IO events for progress.
    Returns immediately with the batch_id.
    Company-scoped: batch and leads are tagged with the user's company_id.
    """
    # Clean and deduplicate keywords
    seen = set()
    clean_keywords = []
    for kw in request.keywords:
        kw_clean = kw.strip()
        if kw_clean and kw_clean.lower() not in seen:
            seen.add(kw_clean.lower())
            clean_keywords.append(kw_clean)

    if not clean_keywords:
        return {"success": False, "error": "No valid keywords provided"}

    location = request.location.strip()
    if not location:
        return {"success": False, "error": "Location is required"}

    # 1. Create batch synchronously to get the ID (company_id set by orchestrator)
    batch = await orchestrator.create_batch(clean_keywords, location, request.limit)

    # 2. Start discovery in background
    background_tasks.add_task(
        orchestrator.run_discovery,
        batch=batch,
        keywords=clean_keywords,
        location=location,
        limit=request.limit,
    )

    return {
        "success": True,
        "message": f"Lead discovery started for {len(clean_keywords)} keywords in {location}",
        "batch_id": batch.id,
        "keywords": clean_keywords,
        "location": location,
        "limit": request.limit,
    }


@router.post("/{batch_id}/stop", response_model=dict)
async def stop_search(
    batch_id: str,
    orchestrator: LeadDiscoveryOrchestrator = Depends(get_lead_orchestrator),
):
    """Manually stop an ongoing search."""
    stmt = select(LeadBatch).where(LeadBatch.id == batch_id)
    result = await orchestrator.session.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if batch:
        batch.status = "stopped"
        batch.reason = "user_stopped"
        await orchestrator.session.commit()
        return {"success": True, "message": "Search stopped manually"}
        
    return {"success": False, "error": "Batch not found"}
