"""PHI encryption at rest using AES-256 (Fernet) for local mode.

In AWS mode, KMS CMK handles encryption transparently at the storage layer.
This module is used for local development to encrypt sensitive fields before
storing in SQLite.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import get_settings
from src.core.errors import HealthcareError


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from the configured encryption key."""
    key_bytes = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(_derive_key(settings.encryption_key))


def encrypt_phi(plaintext: str) -> str:
    """Encrypt a PHI string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_phi(ciphertext: str) -> str:
    """Decrypt a PHI string. Returns plaintext."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise HealthcareError(
            "Failed to decrypt PHI: invalid key or corrupted data",
            code="DECRYPTION_ERROR",
        ) from e
