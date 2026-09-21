from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from platform_app.api.v1 import api_router
from platform_app.config.settings import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Stateless ATREAL lead discovery and "
        "lead capture service."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api",
)


@app.get("/")
async def root():
    return {
        "service": "atreal_lead_capture_agent",
        "status": "running",
        "database": False,
        "authentication": False,
    }