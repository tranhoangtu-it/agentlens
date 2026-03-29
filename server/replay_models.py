"""SQLModel tables and schemas for replay sandbox sessions."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


class ReplaySession(SQLModel, table=True):
    """Stores a replay sandbox session with modified span inputs."""
    __tablename__ = "replay_session"
    id: str = Field(primary_key=True)
    trace_id: str = Field(index=True)
    user_id: str = Field(index=True)
    name: str = "Untitled replay"
    modifications_json: str = "{}"  # {span_id: {input: "new input", ...}}
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_replay_trace_user", "trace_id", "user_id"),
    )


class ReplaySessionIn(BaseModel):
    trace_id: str
    name: str = "Untitled replay"
    modifications: dict = {}  # {span_id: {input: "new input"}}
    notes: str = ""


class ReplaySessionOut(BaseModel):
    id: str
    trace_id: str
    name: str
    modifications: dict
    notes: str
    created_at: str
