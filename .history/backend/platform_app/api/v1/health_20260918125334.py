from fastapi import APIRouter
from sqlalchemy import text
from platform_app.schemas.common import HealthResponse
from platform_app.database.engine import async_engine
from platform_app.config.settings import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    
    # Check database connection
    db_status = "ok"
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        
    # Build health response
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=settings.APP_VERSION,
        database=db_status,
        socketio="ok",  # Assuming Socket.IO server is running if FastAPI is responding
        storage="ok",   # We can add storage directory checks here later
    )
