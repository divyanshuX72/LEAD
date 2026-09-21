from fastapi import APIRouter

from platform_app.config.settings import get_settings


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health():
    settings = get_settings()

    return {
        "status": "ok",
        "service": "atreal_lead_capture_agent",
        "version": settings.APP_VERSION,
        "database": False,
        "authentication": False,
    }