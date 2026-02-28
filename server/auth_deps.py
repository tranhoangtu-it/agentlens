"""FastAPI dependency for extracting current user from JWT or API key."""

from typing import Optional

from fastapi import Depends, HTTPException, Request

from auth_jwt import decode_token
from auth_models import User
from auth_storage import get_user_by_id, validate_api_key


def get_current_user(request: Request) -> User:
    """Extract authenticated user from Authorization header (JWT or API key).

    Supports:
      - Bearer <jwt_token>  (dashboard sessions)
      - ApiKey <al_xxx>     (SDK ingestion)
    """
    auth = request.headers.get("Authorization", "")

    # JWT Bearer token
    if auth.startswith("Bearer "):
        token = auth[7:]
        payload = decode_token(token)
        if not payload:
            raise HTTPException(401, "Invalid or expired token")
        user = get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(401, "User not found")
        return user

    # API Key
    if auth.startswith("ApiKey "):
        raw_key = auth[7:]
        user = validate_api_key(raw_key)
        if not user:
            raise HTTPException(401, "Invalid API key")
        return user

    # Also check X-API-Key header (SDK convenience)
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        user = validate_api_key(api_key)
        if not user:
            raise HTTPException(401, "Invalid API key")
        return user

    raise HTTPException(401, "Missing authentication")


def get_optional_user(request: Request) -> Optional[User]:
    """Like get_current_user but returns None instead of 401.

    Used during migration period when auth is optional.
    """
    try:
        return get_current_user(request)
    except HTTPException:
        return None
