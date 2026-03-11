"""Encryption utilities for sensitive tokens (GitLab PAT, etc.)."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from jwt_secret_key."""
    key_bytes = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_token(plain: str) -> str:
    """Encrypt a plaintext token. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a token back to plaintext."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def mask_token(plain: str) -> str:
    """Return masked version: first 4 chars + ****."""
    if len(plain) <= 4:
        return "****"
    return plain[:4] + "****"
