"""
Security Utilities

File validation, sanitization, and upload security.
"""

import re
import unicodedata
from pathlib import Path

from platform_app.config.settings import get_settings
from platform_app.core.exceptions import (
    FileTooLargeException,
    UnsupportedFileTypeException,
    ValidationException,
)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and special char issues."""
    # Normalize unicode
    filename = unicodedata.normalize("NFKD", filename)
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Keep only safe characters
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    # Collapse whitespace
    filename = re.sub(r'\s+', '_', filename.strip())
    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")
    # Limit length
    if len(filename) > 200:
        name, ext = Path(filename).stem[:180], Path(filename).suffix
        filename = name + ext
    return filename or "unnamed_file"


def validate_file_upload(filename: str, file_size: int) -> None:
    """Validate an uploaded file for security."""
    settings = get_settings()

    # Check file size
    if file_size > settings.max_upload_size_bytes:
        raise FileTooLargeException(settings.MAX_UPLOAD_SIZE_MB)

    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions_list:
        raise UnsupportedFileTypeException(ext)

    # Check for suspicious filenames
    if not filename or filename.strip() == "":
        raise ValidationException("Filename cannot be empty")

    # Check for double extensions (e.g., .php.jpg)
    parts = filename.rsplit(".", maxsplit=2)
    if len(parts) > 2:
        inner_ext = f".{parts[-2]}"
        suspicious_exts = {".php", ".exe", ".bat", ".cmd", ".sh", ".py", ".js"}
        if inner_ext.lower() in suspicious_exts:
            raise ValidationException("Suspicious file extension detected")


def get_file_type(extension: str) -> str:
    """Get a human-readable file type from extension."""
    type_map = {
        ".pdf": "PDF Document",
        ".docx": "Word Document",
        ".doc": "Word Document (Legacy)",
        ".txt": "Text File",
        ".csv": "CSV Spreadsheet",
        ".xlsx": "Excel Spreadsheet",
        ".xls": "Excel Spreadsheet (Legacy)",
        ".md": "Markdown Document",
        ".png": "PNG Image",
        ".jpg": "JPEG Image",
        ".jpeg": "JPEG Image",
        ".gif": "GIF Image",
        ".webp": "WebP Image",
    }
    return type_map.get(extension.lower(), "Unknown File")
