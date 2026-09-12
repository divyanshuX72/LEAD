"""
Leads & Batches API Router — Lead Agent (Multi-Tenant)

Batch management, lead listing, dashboard stats, and deletion.
All endpoints are authenticated and company-scoped.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from platform_app.database.session import get_db_session
from platform_app.core.auth import get_current_user
from platform_app.models.user import User
from platform_app.api.dependencies import (
    get_lead_repo, get_batch_repo, get_export_service,
)
from platform_app.schemas.lead import (
    LeadBatchResponse, LeadResponse, DashboardStats,
    ExportRequest, ExportSelectedRequest, ExportResponse,
)
from platform_app.repositories.lead_repositories import (
    LeadRepository, LeadBatchRepository,
)
from platform_app.services.export_service import ExportService

router = APIRouter(prefix="/leads", tags=["Lead Agent"])


# ── Dashboard ────────────────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    lead_repo: LeadRepository = Depends(get_lead_repo),
    batch_repo: LeadBatchRepository = Depends(get_batch_repo),
):
    """Get aggregate stats for the lead dashboard (company-scoped)."""
    total_leads = await lead_repo.count_total()
    total_batches = await batch_repo.get_batch_count()
    unique_emails = await lead_repo.count_unique_emails()
    unique_phones = await lead_repo.count_unique_phones()

    # Get last search date
    batches = await batch_repo.get_all_ordered(limit=1)
    last_search = batches[0].created_at if batches else None

    return DashboardStats(
        total_leads=total_leads,
        total_batches=total_batches,
        last_search=last_search,
        unique_emails=unique_emails,
        unique_phones=unique_phones,
    )


# ── Lead Batches ─────────────────────────────────────────────────────────

@router.get("/lead-batches", response_model=list[LeadBatchResponse])
async def list_batches(
    limit: int = Query(100, le=500),
    batch_repo: LeadBatchRepository = Depends(get_batch_repo),
):
    """List all search batches (company-scoped)."""
    batches = await batch_repo.get_all_ordered(limit=limit)
    return [LeadBatchResponse.from_orm_with_keywords(b) for b in batches]


@router.get("/lead-batches/{batch_id}", response_model=LeadBatchResponse)
async def get_batch(
    batch_id: str,
    batch_repo: LeadBatchRepository = Depends(get_batch_repo),
):
    """Get a single batch with metadata (company-scoped)."""
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return LeadBatchResponse.from_orm_with_keywords(batch)


@router.get("/lead-batches/{batch_id}/leads", response_model=list[LeadResponse])
async def get_batch_leads(
    batch_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, le=1000),
    batch_repo: LeadBatchRepository = Depends(get_batch_repo),
    lead_repo: LeadRepository = Depends(get_lead_repo),
):
    """Get all leads in a batch (company-scoped)."""
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    leads = await lead_repo.get_by_batch(batch_id, skip=skip, limit=limit)
    return leads


@router.delete("/lead-batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    batch_repo: LeadBatchRepository = Depends(get_batch_repo),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a batch and all its leads (company-scoped)."""
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    await session.delete(batch)
    await session.commit()
    return {"success": True, "message": f"Batch '{batch.name}' deleted"}


# ── Leads ────────────────────────────────────────────────────────────────

@router.get("/leads", response_model=list[LeadResponse])
async def list_leads(
    query: str = "",
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    lead_repo: LeadRepository = Depends(get_lead_repo),
):
    """List all leads with optional search (company-scoped)."""
    if query:
        return await lead_repo.search(query, skip=skip, limit=limit)
    return await lead_repo.get_all_leads(skip=skip, limit=limit)


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    lead_repo: LeadRepository = Depends(get_lead_repo),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a single lead (company-scoped)."""
    lead = await lead_repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await session.delete(lead)
    await session.commit()
    return {"success": True}


# ── Exports ──────────────────────────────────────────────────────────────

@router.post("/exports/batch/{batch_id}", response_model=ExportResponse)
async def export_batch(
    batch_id: str,
    request: ExportRequest,
    export_service: ExportService = Depends(get_export_service),
):
    """Export a single batch to CSV or XLSX (company-scoped)."""
    try:
        job = await export_service.export_batch(batch_id, fmt=request.format)
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/exports/selected", response_model=ExportResponse)
async def export_selected(
    request: ExportSelectedRequest,
    export_service: ExportService = Depends(get_export_service),
):
    """Export selected batches to CSV or XLSX (company-scoped)."""
    try:
        job = await export_service.export_selected(
            batch_ids=request.batch_ids, fmt=request.format
        )
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/exports/all", response_model=ExportResponse)
async def export_all(
    request: ExportRequest,
    export_service: ExportService = Depends(get_export_service),
):
    """Export all leads to CSV or XLSX (company-scoped)."""
    job = await export_service.export_all(
        fmt=request.format, unique_only=request.unique_only
    )
    return job


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Download an exported file (company-scoped)."""
    from platform_app.models.export_job import ExportJob
    from sqlalchemy import select

    stmt = select(ExportJob).where(
        ExportJob.id == export_id,
        ExportJob.company_id == user.company_id,
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job or not job.file_path:
        raise HTTPException(status_code=404, detail="Export not found")

    file_path = Path(job.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file no longer exists")

    media_type = "text/csv" if job.export_type == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        path=str(file_path),
        filename=job.file_name or file_path.name,
        media_type=media_type,
    )
