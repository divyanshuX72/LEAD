"""
API v1 Router — Lead Agent (Simplified)

Only includes Lead Agent routers + health + auth.
"""

from fastapi import APIRouter

# Infrastructure
from platform_app.api.v1.health import router as health_router
from platform_app.api.v1.auth import router as auth_router

# Lead Agent
from platform_app.api.routers.leads import router as leads_router
from platform_app.api.routers.lead_search import router as lead_search_router

api_router = APIRouter()

# Infrastructure
api_router.include_router(health_router)
api_router.include_router(auth_router)

# Lead Agent
api_router.include_router(leads_router)
api_router.include_router(lead_search_router)
