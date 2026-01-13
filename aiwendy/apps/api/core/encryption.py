"""Encryption utilities for sensitive data."""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet

from config import get_settings

settings = get_settings()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, key: Optional[str] = None):
        """Initialize encryption service with key."""
        if key:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            # Use JWT secret as base for encryption key
            # In production, use a separate encryption key
            key_base = settings.jwt_secret[:32].ljust(32, "0")
            key_bytes = base64.urlsafe_b64encode(key_base.encode()[:32])
            self.cipher = Fernet(key_bytes)

    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64 encoded result."""
        if not data:
            return ""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded data and return original string."""
        if not encrypted_data:
            return ""
        try:
            decoded = base64.b64decode(encrypted_data.encode("utf-8"))
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode("utf-8")
        except Exception:
            # If decryption fails, return empty string
            return ""

    def mask_api_key(self, key: str) -> str:
        """Mask an API key for display (show first 7 and last 4 characters)."""
        if not key or len(key) < 15:
            return "***"
        return f"{key[:7]}...{key[-4:]}"


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
