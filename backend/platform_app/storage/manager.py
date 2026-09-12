"""
Storage Manager

Handles file storage operations: save, retrieve, delete, move.
Never mixes original files with processed files.
"""

import shutil
import aiofiles
from pathlib import Path
from uuid import uuid4

from platform_app.storage.paths import get_storage_paths, get_company_storage_path
from platform_app.core.security import sanitize_filename
from platform_app.core.exceptions import StorageException


class StorageManager:
    """Manages file storage operations."""

    @staticmethod
    async def save_upload(
        file_content: bytes,
        filename: str,
        company_id: str,
    ) -> dict:
        """
        Save an uploaded file to the originals directory.
        Returns dict with storage_path, stored_filename, and file_size.
        """
        safe_name = sanitize_filename(filename)
        unique_name = f"{uuid4().hex[:8]}_{safe_name}"
        company_path = get_company_storage_path(company_id, "originals")
        file_path = company_path / unique_name

        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)

            return {
                "storage_path": str(file_path),
                "stored_filename": unique_name,
                "file_size": len(file_content),
            }
        except Exception as e:
            raise StorageException(f"Failed to save file: {e}")

    @staticmethod
    async def save_logo(
        file_content: bytes,
        filename: str,
        company_id: str,
    ) -> str:
        """Save a company logo and return the storage path."""
        safe_name = sanitize_filename(filename)
        unique_name = f"{company_id}_{safe_name}"
        paths = get_storage_paths()
        logo_path = paths["logos"] / unique_name

        try:
            async with aiofiles.open(logo_path, "wb") as f:
                await f.write(file_content)
            return str(logo_path)
        except Exception as e:
            raise StorageException(f"Failed to save logo: {e}")

    @staticmethod
    async def delete_file(storage_path: str) -> bool:
        """Delete a file from storage."""
        try:
            path = Path(storage_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            raise StorageException(f"Failed to delete file: {e}")

    @staticmethod
    async def get_file_content(storage_path: str) -> bytes:
        """Read file content from storage."""
        try:
            async with aiofiles.open(storage_path, "rb") as f:
                return await f.read()
        except FileNotFoundError:
            raise StorageException(f"File not found: {storage_path}")
        except Exception as e:
            raise StorageException(f"Failed to read file: {e}")

    @staticmethod
    def get_storage_stats() -> dict:
        """Get storage usage statistics."""
        paths = get_storage_paths()
        stats = {}

        for name, path in paths.items():
            if name == "root":
                continue
            total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            file_count = sum(1 for f in path.rglob("*") if f.is_file())
            stats[name] = {
                "size": total_size,
                "files": file_count,
            }

        stats["total_size"] = sum(s["size"] for s in stats.values())
        stats["total_files"] = sum(s["files"] for s in stats.values())
        return stats
