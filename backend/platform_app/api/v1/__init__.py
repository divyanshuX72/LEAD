from fastapi import APIRouter

from platform_app.api.v1.health import router as health_router
from platform_app.api.v1.leads import router as leads_router


api_router = APIRouter()

api_router.include_router(
    health_router,
    prefix="/v1",
)

api_router.include_router(
    leads_router,
    prefix="/v1",
)