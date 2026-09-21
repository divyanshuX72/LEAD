"""
Lead Intelligence Platform - Main Entry Point

FastAPI application with Socket.IO integration.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from platform_app.config.settings import get_settings
from platform_app.core.exceptions import AppException
from platform_app.core.events import socket_app
from platform_app.api.v1 import api_router
from platform_app.database.init_db import init_database

from platform_app.database.engine import async_engine

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_database()
    yield
    # Cleanly dispose async DB engine on shutdown
    await async_engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Lead Intelligence Platform API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lead.atrealstudios.in",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    
)

# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": exc.message, "error_code": exc.error_code},
    )

# Include REST API routes
app.include_router(api_router, prefix="/api/v1")

# Mount Socket.IO application
app.mount("/", socket_app)


if __name__ == "__main__":
    uvicorn.run(
        "platform_app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )
