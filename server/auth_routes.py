"""FastAPI router for authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from auth_deps import get_current_user
from auth_jwt import create_token
from auth_models import LoginIn, RegisterIn, User
from auth_storage import (
    create_api_key,
    create_user,
    delete_api_key,
    get_user_by_email,
    list_user_api_keys,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn):
    """Register a new user account."""
    if get_user_by_email(body.email):
        raise HTTPException(409, "Email already registered")
    if len(body.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    user = create_user(body.email, body.password, body.display_name)
    token = create_token(user.id, user.email)
    return {"user_id": user.id, "email": user.email, "token": token}


@router.post("/login")
def login(body: LoginIn):
    """Authenticate with email/password, return JWT token."""
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user.id, user.email)
    return {"user_id": user.id, "email": user.email, "token": token}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    """Return current authenticated user profile."""
    return {
        "user_id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
    }


# ── API Keys ─────────────────────────────────────────────────────────────────


@router.post("/api-keys", status_code=201)
def create_key(name: str = "default", user: User = Depends(get_current_user)):
    """Create a new API key. Full key is returned only once."""
    api_key, full_key = create_api_key(user.id, name)
    return {
        "id": api_key.id,
        "key": full_key,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get("/api-keys")
def list_keys(user: User = Depends(get_current_user)):
    """List all API keys for current user (without full key)."""
    keys = list_user_api_keys(user.id)
    return {
        "keys": [
            {
                "id": k.id,
                "key_prefix": k.key_prefix,
                "name": k.name,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]
    }


@router.delete("/api-keys/{key_id}", status_code=204)
def delete_key(key_id: str, user: User = Depends(get_current_user)):
    """Delete an API key owned by current user."""
    if not delete_api_key(key_id, user.id):
        raise HTTPException(404, "API key not found")
