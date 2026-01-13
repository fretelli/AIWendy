"""Encryption utilities for sensitive data."""

import base64
import hashlib
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
            # Use provided key (should be base64 encoded Fernet key)
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        elif settings.encryption_key:
            # Use dedicated encryption key from settings
            # Derive Fernet key using HKDF (proper key derivation)
            derived_key = self._derive_fernet_key(settings.encryption_key)
            self.cipher = Fernet(derived_key)
        else:
            # Fallback: derive from JWT secret (less secure, but backwards compatible)
            # This should trigger a warning in _validate_security_config()
            derived_key = self._derive_fernet_key(settings.jwt_secret)
            self.cipher = Fernet(derived_key)

    def _derive_fernet_key(self, secret: str) -> bytes:
        """Derive a Fernet-compatible key from a secret using HKDF."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        # Use HKDF to derive a proper 32-byte key
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"aiwendy-encryption-salt-v1",  # Static salt for deterministic key
            info=b"api-key-encryption",
        )
        derived = kdf.derive(secret.encode())
        return base64.urlsafe_b64encode(derived)

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
