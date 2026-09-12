"""
Hash Utilities

SHA-256 hashing for file duplicate detection.
"""

import hashlib
from pathlib import Path


def compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """Compute the hash of a file for duplicate detection."""
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def compute_content_hash(content: bytes, algorithm: str = "sha256") -> str:
    """Compute hash of raw bytes content."""
    hash_func = hashlib.new(algorithm)
    hash_func.update(content)
    return hash_func.hexdigest()
