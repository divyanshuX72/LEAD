"""
Storage Path Configuration

Defines the structured storage directory layout.
"""

from pathlib import Path
from platform_app.config.settings import get_settings


def get_storage_paths() -> dict[str, Path]:
    """Get all storage directory paths, creating them if needed."""
    settings = get_settings()
    root = Path(settings.STORAGE_PATH).resolve()

    paths = {
        "root": root,
        "originals": root / "originals",
        "processed": root / "processed",
        "temp": root / "temp",
        "previews": root / "previews",
        "embeddings": root / "embeddings",
        "logos": root / "logos",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def get_company_storage_path(company_id: str, category: str = "originals") -> Path:
    """Get storage path for a specific company's files."""
    paths = get_storage_paths()
    company_path = paths[category] / company_id
    company_path.mkdir(parents=True, exist_ok=True)
    return company_path
