"""
Lead Intelligence Platform - Configuration Module

Centralized settings management using pydantic-settings.
All configuration is loaded from environment variables / .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    APP_NAME: str = "Lead Intelligence Platform"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "mysql+aiomysql://root@localhost:3306/lead"
    DATABASE_SYNC_URL: str = "mysql+pymysql://root@localhost:3306/lead"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173
    FRONTEND_URL: str = "http://localhost:5173"

    # Storage
    STORAGE_PATH: str = "./storage"

    # Security
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.md,.png,.jpg,.jpeg,.gif,.webp"

    # ── Phase 3: JWT Authentication ─────────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Phase 2: Search API Keys ─────────────────────────────────────────
    SERPER_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    GOOGLE_MAPS_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None

    # ── Phase 2: AI / LLM ───────────────────────────────────────────────
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── Phase 2: Research Config ─────────────────────────────────────────
    MAX_CONCURRENT_RESEARCH: int = 3
    RESEARCH_TIMEOUT_SECONDS: int = 30
    MAX_PAGES_PER_SITE: int = 15

    # ── Phase 2: Search Config ───────────────────────────────────────────
    DEFAULT_SEARCH_LIMIT: int = 50
    MAX_SEARCH_RESULTS: int = 200

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def storage_root(self) -> Path:
        path = Path(self.STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
