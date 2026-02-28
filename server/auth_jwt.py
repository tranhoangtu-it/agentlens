"""JWT encode/decode helpers for AgentLens auth."""

import os
import secrets
from datetime import datetime, timezone, timedelta

import jwt

# Auto-generate secret if not set (persists for process lifetime)
_JWT_SECRET = os.environ.get("AGENTLENS_JWT_SECRET", secrets.token_hex(32))
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24


def create_token(user_id: str, email: str) -> str:
    """Create a JWT token with user_id and email claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=_JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
