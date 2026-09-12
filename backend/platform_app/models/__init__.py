"""
Models Package — Lead Agent (Multi-Tenant)

Exports all ORM models for the focused Lead Agent.
"""

from platform_app.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid

# Multi-tenant core
from platform_app.models.company import Company

# Infrastructure
from platform_app.models.workspace import Organization, Workspace
from platform_app.models.user import User
from platform_app.models.auth_models import Session, Role, Permission, RoleType

# Lead Agent core
from platform_app.models.lead_batch import LeadBatch, BatchStatus
from platform_app.models.lead_batch_keyword import LeadBatchKeyword
from platform_app.models.lead import Lead
from platform_app.models.lead_source import LeadSource
from platform_app.models.export_job import ExportJob, ExportStatus

__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "generate_uuid",
    # Multi-tenant
    "Company",
    # Infrastructure
    "Organization",
    "Workspace",
    "User",
    "Session",
    "Role",
    "Permission",
    "RoleType",
    # Lead Agent
    "LeadBatch",
    "BatchStatus",
    "LeadBatchKeyword",
    "Lead",
    "LeadSource",
    "ExportJob",
    "ExportStatus",
]
