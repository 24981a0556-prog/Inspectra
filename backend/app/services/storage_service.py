"""
StorageService — abstraction layer for file storage.

Current backend: LocalStorageService (saves to disk, served as static files)
Future backend: S3StorageService (upload to AWS S3)

To switch backends, change STORAGE_BACKEND in .env.
"""
import abc
import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple

from app.core.config import settings


class StorageService(abc.ABC):
    """Abstract base class for file storage backends."""

    @abc.abstractmethod
    def store(
        self,
        file_bytes: bytes,
        filename: str,
        inspection_id: int,
        content_type: str,
    ) -> Tuple[str, str]:
        """
        Store the file and return (url_or_path, sha256_hash).
        The returned URL is what gets persisted in the DB and sent to the client.
        """
        ...


class LocalStorageService(StorageService):
    """
    Stores files on the local filesystem under UPLOAD_DIR/inspections/{id}/.
    Files are served by FastAPI's StaticFiles mount at /uploads/.
    """

    def __init__(self):
        self.base_dir = Path(settings.LOCAL_UPLOAD_DIR)

    def store(
        self,
        file_bytes: bytes,
        filename: str,
        inspection_id: int,
        content_type: str,
    ) -> Tuple[str, str]:
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Sanitise extension
        ext = Path(filename).suffix.lower() if filename else ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"

        dir_path = self.base_dir / "inspections" / str(inspection_id)
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / safe_name
        file_path.write_bytes(file_bytes)

        # URL served by FastAPI static mount
        url = f"/uploads/inspections/{inspection_id}/{safe_name}"
        return url, file_hash


class S3StorageService(StorageService):
    """
    TODO: Implement S3 storage for production.
    Install: pip install boto3
    """

    def store(self, file_bytes, filename, inspection_id, content_type) -> Tuple[str, str]:
        raise NotImplementedError("S3 storage is not yet implemented. Set STORAGE_BACKEND=local.")


def get_storage_service() -> StorageService:
    """Factory — returns the configured storage backend."""
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorageService()
    elif backend == "s3":
        return S3StorageService()
    else:
        raise ValueError(f"Unknown STORAGE_BACKEND: '{backend}'. Use 'local' or 's3'.")
