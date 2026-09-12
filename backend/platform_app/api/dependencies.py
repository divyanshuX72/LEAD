"""
API Dependencies — Lead Agent (Multi-Tenant)

FastAPI dependency injection for all Lead Agent services.
All data access is scoped by company_id from the authenticated user.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.database.session import get_db_session
from platform_app.core.auth import get_current_user
from platform_app.models.user import User
from platform_app.repositories.lead_repositories import (
    LeadRepository,
    LeadBatchRepository,
    LeadBatchKeywordRepository,
    LeadSourceRepository,
    ExportJobRepository,
)
from platform_app.services.lead_discovery_orchestrator import LeadDiscoveryOrchestrator
from platform_app.services.export_service import ExportService


# ── Repositories (company-scoped) ────────────────────────────────────────

def get_lead_repo(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> LeadRepository:
    return LeadRepository(session, company_id=user.company_id)

def get_batch_repo(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> LeadBatchRepository:
    return LeadBatchRepository(session, company_id=user.company_id)

def get_batch_keyword_repo(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> LeadBatchKeywordRepository:
    return LeadBatchKeywordRepository(session)

def get_lead_source_repo(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> LeadSourceRepository:
    return LeadSourceRepository(session)

def get_export_job_repo(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ExportJobRepository:
    return ExportJobRepository(session, company_id=user.company_id)


# ── Services ─────────────────────────────────────────────────────────────

def get_lead_orchestrator(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> LeadDiscoveryOrchestrator:
    return LeadDiscoveryOrchestrator(session, company_id=user.company_id)

def get_export_service(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ExportService:
    return ExportService(session, company_id=user.company_id)
