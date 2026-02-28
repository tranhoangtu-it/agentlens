"""CRUD functions for users and API keys."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from sqlmodel import Session, select

from auth_models import ApiKey, User
from storage import _get_engine


def create_user(
    email: str, password: str, display_name: Optional[str] = None, is_admin: bool = False,
) -> User:
    """Create a new user with bcrypt-hashed password."""
    engine = _get_engine()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        password_hash=pw_hash,
        display_name=display_name,
        is_admin=is_admin,
    )
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def get_user_by_email(email: str) -> Optional[User]:
    """Look up user by email (case-insensitive)."""
    engine = _get_engine()
    with Session(engine) as session:
        return session.exec(
            select(User).where(User.email == email.lower().strip())
        ).first()


def get_user_by_id(user_id: str) -> Optional[User]:
    """Look up user by ID."""
    engine = _get_engine()
    with Session(engine) as session:
        return session.get(User, user_id)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_api_key(user_id: str, name: str = "default") -> tuple[ApiKey, str]:
    """Create API key. Returns (ApiKey, full_key). Full key shown only once."""
    engine = _get_engine()
    full_key = "al_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:8] + "..."

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
    )
    with Session(engine) as session:
        session.add(api_key)
        session.commit()
        session.refresh(api_key)
    return api_key, full_key


def validate_api_key(raw_key: str) -> Optional[User]:
    """Validate API key, return owning User or None. Updates last_used_at."""
    engine = _get_engine()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    with Session(engine) as session:
        api_key = session.exec(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        ).first()
        if not api_key:
            return None
        api_key.last_used_at = datetime.now(timezone.utc)
        session.add(api_key)
        session.commit()
        user = session.get(User, api_key.user_id)
        return user


def list_user_api_keys(user_id: str) -> list[ApiKey]:
    """List all API keys for a user."""
    engine = _get_engine()
    with Session(engine) as session:
        return list(session.exec(
            select(ApiKey).where(ApiKey.user_id == user_id)
        ).all())


def delete_api_key(key_id: str, user_id: str) -> bool:
    """Delete an API key owned by user. Returns True if deleted."""
    engine = _get_engine()
    with Session(engine) as session:
        api_key = session.get(ApiKey, key_id)
        if not api_key or api_key.user_id != user_id:
            return False
        session.delete(api_key)
        session.commit()
    return True
