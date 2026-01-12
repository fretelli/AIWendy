"""Local file storage service for chat attachments."""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

from core.logging import get_logger

logger = get_logger(__name__)


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        """Upload a file and return the storage path."""
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Get a URL for accessing the file."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete a file from storage."""
        pass

    @abstractmethod
    async def get_file_path(self, path: str) -> Optional[Path]:
        """Get the full filesystem path for a stored file."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider."""

    def __init__(self, base_path: str = "./uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"LocalStorageProvider initialized with base path: {self.base_path.absolute()}"
        )

    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        """
        Upload a file to local storage.

        Args:
            file: File-like object to upload
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            Relative storage path (e.g., "2024/01/uuid-filename.ext")
        """
        # Generate unique path: year/month/uuid-filename
        date_prefix = datetime.utcnow().strftime("%Y/%m")
        safe_filename = self._sanitize_filename(filename)
        unique_name = f"{uuid.uuid4()}-{safe_filename}"
        rel_path = f"{date_prefix}/{unique_name}"

        # Create full path
        full_path = self.base_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            content = file.read()
            with open(full_path, "wb") as f:
                f.write(content)

            logger.info(f"File uploaded: {rel_path} ({len(content)} bytes)")
            return rel_path

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    async def get_url(self, path: str) -> str:
        """
        Get a URL for accessing the file.

        Args:
            path: Relative storage path

        Returns:
            API URL for downloading the file
        """
        return f"/api/v1/files/download/{path}"

    async def delete(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: Relative storage path

        Returns:
            True if deleted successfully, False otherwise
        """
        full_path = self.base_path / path
        try:
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted: {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            return False

    async def get_file_path(self, path: str) -> Optional[Path]:
        """
        Get the full filesystem path for a stored file.

        Args:
            path: Relative storage path

        Returns:
            Full Path object if file exists, None otherwise
        """
        full_path = self.base_path / path
        if full_path.exists():
            return full_path
        return None

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other issues.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Get just the filename without any path
        filename = os.path.basename(filename)

        # Replace potentially dangerous characters
        for char in ["/", "\\", "..", "\x00"]:
            filename = filename.replace(char, "_")

        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[: 200 - len(ext)] + ext

        return filename or "unnamed"


# Singleton instance
_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """Get the storage provider singleton."""
    global _storage_provider
    if _storage_provider is None:
        # Default to local storage
        # In production, this could be configured via environment variables
        _storage_provider = LocalStorageProvider("./uploads")
    return _storage_provider


def set_storage_provider(provider: StorageProvider) -> None:
    """Set a custom storage provider (for testing or alternative storage)."""
    global _storage_provider
    _storage_provider = provider
