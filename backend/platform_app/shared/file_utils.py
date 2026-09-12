"""
File Utilities

Common file operations and helpers.
"""

from pathlib import Path


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_extension(filename: str) -> str:
    """Get lowercase file extension."""
    return Path(filename).suffix.lower()


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if needed."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
