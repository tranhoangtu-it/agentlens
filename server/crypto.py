"""Symmetric encryption helpers for storing sensitive values (API keys)."""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_secret() -> str:
    """Read JWT secret from env. Returns empty string if not set."""
    return os.environ.get("AGENTLENS_JWT_SECRET", "")


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the JWT secret. Raises if no secret is set."""
    secret = _get_secret()
    if not secret:
        raise RuntimeError(
            "AGENTLENS_JWT_SECRET must be set to store encrypted API keys. "
            "Set this environment variable and restart the server."
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str | None:
    """Decrypt a ciphertext. Returns None if decryption fails."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        logger.warning("Failed to decrypt value — key may have changed.")
        return None
