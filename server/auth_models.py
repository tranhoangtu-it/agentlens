"""SQLModel tables and Pydantic schemas for authentication."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


# ── Database tables ──────────────────────────────────────────────────────────


class User(SQLModel, table=True):
    """Registered user account."""
    id: str = Field(primary_key=True)
    email: str = Field(sa_column_kwargs={"unique": True}, index=True)
    password_hash: str
    display_name: Optional[str] = None
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ApiKey(SQLModel, table=True):
    """API key for SDK authentication. Stores SHA-256 hash, never plaintext."""
    __tablename__ = "api_key"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    key_hash: str  # SHA-256 of full key
    key_prefix: str  # First 8 chars for display: "al_xxxx..."
    name: str = Field(default="default")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_used_at: Optional[datetime] = None

    __table_args__ = (
        Index("ix_api_key_hash", "key_hash"),
    )


# ── Request schemas ──────────────────────────────────────────────────────────


class RegisterIn(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str
