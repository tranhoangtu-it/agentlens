"""JWT encode/decode helpers for AgentLens auth."""

import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

import jwt

logger = logging.getLogger(__name__)

# Auto-generate secret if not set (persists for process lifetime only — tokens
# will be invalidated on every restart without AGENTLENS_JWT_SECRET configured)
_jwt_secret_env = os.environ.get("AGENTLENS_JWT_SECRET")
if _jwt_secret_env:
    _JWT_SECRET = _jwt_secret_env
else:
    _JWT_SECRET = secrets.token_hex(32)
    logger.warning(
        "AGENTLENS_JWT_SECRET is not set — a random secret was generated. "
        "All JWT tokens will be invalidated on server restart. "
        "Set AGENTLENS_JWT_SECRET in production to persist sessions."
    )
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
