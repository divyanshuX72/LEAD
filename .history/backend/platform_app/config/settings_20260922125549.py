from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ATREAL Lead Capture Agent"
    APP_VERSION: str = "2.0.0"

    DEBUG: bool = True

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # External discovery providers
    SERPER_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    GOOGLE_MAPS_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None

    # Optional enrichment
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Data Service
    DATA_SERVICE_URL: str = "http://127.0.0.1:8001"
    DATA_SERVICE_TIMEOUT_SECONDS: float = 20.0

    # Discovery
    MAX_CONCURRENT_RESEARCH: int = 5
    SEARCH_TIMEOUT_SECONDS: float = 15.0
    SCRAPE_TIMEOUT_SECONDS: float = 8.0
    DISCOVERY_TIMEOUT_SECONDS: float = 45.0

    MAX_SEARCH_RESULTS_PER_PROVIDER: int = 20
    MAX_PAGES_PER_PROVIDER: int = 4

    MAX_WEBSITE_PAGES: int = 8

    DEFAULT_SEARCH_LIMIT: int = 50
    MAX_SEARCH_LIMIT: int = 500

    # ATREAL target
    TARGET_CUSTOMER: str = "Real Estate Developers"
    PRODUCT_NAME: str = "ATREAL Immersia"


@lru_cache
def get_settings() -> Settings:
    return Settings()