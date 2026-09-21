from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration for the ATREAL Lead Capture Agent.

    This service is intentionally stateless.
    It does not contain database credentials, authentication
    configuration, workspace configuration, or CRM configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ATREAL Lead Capture Agent"
    APP_VERSION: str = "1.0.0"

    DEBUG: bool = True

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # External discovery providers
    SERPER_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    GOOGLE_MAPS_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None

    # Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Discovery controls
    MAX_CONCURRENT_RESEARCH: int = 5
    SEARCH_TIMEOUT_SECONDS: float = 15.0
    SCRAPE_TIMEOUT_SECONDS: float = 8.0
    DISCOVERY_TIMEOUT_SECONDS: float = 45.0

    MAX_SEARCH_RESULTS_PER_PROVIDER: int = 20
    MAX_PAGES_PER_PROVIDER: int = 4
    MAX_WEBSITE_PAGES: int = 8

    DEFAULT_SEARCH_LIMIT: int = 50
    MAX_SEARCH_LIMIT: int = 500

    # ATREAL-specific defaults
    TARGET_CUSTOMER: str = "Real Estate Developers"
    PRODUCT_NAME: str = "ATREAL Immersia"


@lru_cache
def get_settings() -> Settings:
    return Settings()