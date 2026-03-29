"""SQLModel tables and Pydantic schemas for prompt versioning."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


# ── Database tables ──────────────────────────────────────────────────────────


class PromptTemplate(SQLModel, table=True):
    """Named prompt template owned by a user, tracks latest version number."""
    __tablename__ = "prompt_template"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    name: str
    latest_version: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_prompt_user_name", "user_id", "name", unique=True),
    )


class PromptVersion(SQLModel, table=True):
    """Immutable snapshot of prompt content at a specific version number."""
    __tablename__ = "prompt_version"

    id: str = Field(primary_key=True)
    prompt_id: str = Field(index=True)
    user_id: str = Field(index=True)
    version: int
    content: str
    variables_json: str = Field(default="[]")   # JSON array of variable names
    metadata_json: str = Field(default="{}")     # JSON object of arbitrary metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_pv_prompt_version", "prompt_id", "version", unique=True),
    )


# ── Request schemas ──────────────────────────────────────────────────────────


class PromptTemplateIn(BaseModel):
    name: str


class PromptVersionIn(BaseModel):
    content: str
    variables: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


# ── Response schemas ─────────────────────────────────────────────────────────


class PromptVersionOut(BaseModel):
    id: str
    prompt_id: str
    version: int
    content: str
    variables_json: str
    metadata_json: str
    created_at: datetime


class PromptTemplateOut(BaseModel):
    id: str
    user_id: str
    name: str
    latest_version: int
    created_at: datetime
    updated_at: datetime
    versions: list[PromptVersionOut] = []
