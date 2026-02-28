"""SQLModel tables and Pydantic schemas for alerting system."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


# ── Database tables ──────────────────────────────────────────────────────────


class AlertRule(SQLModel, table=True):
    """User-configurable rule that triggers alerts on agent behavior anomalies."""
    __tablename__ = "alert_rule"

    id: str = Field(primary_key=True)
    name: str
    user_id: Optional[str] = Field(default=None, index=True)
    agent_name: str = Field(index=True)  # "*" = all agents
    metric: str  # "cost", "error_rate", "latency", "missing_span"
    operator: str = Field(default="gt")  # "gt", "lt", "gte", "lte"
    threshold: float  # absolute value or multiplier (depending on mode)
    mode: str = Field(default="absolute")  # "absolute" or "relative"
    window_size: int = Field(default=10)  # last N traces for baseline
    enabled: bool = Field(default=True, index=True)
    webhook_url: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_alert_rule_agent_metric", "agent_name", "metric"),
    )


class AlertEvent(SQLModel, table=True):
    """Fired alert event linking a rule to a triggering trace."""
    __tablename__ = "alert_event"

    id: str = Field(primary_key=True)
    rule_id: str = Field(index=True)
    trace_id: str = Field(index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    agent_name: str = Field(index=True)
    metric: str
    value: float
    threshold: float
    message: str
    resolved: bool = Field(default=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True,
    )

    __table_args__ = (
        Index("ix_alert_event_rule_created", "rule_id", "created_at"),
    )


# ── Request schemas ──────────────────────────────────────────────────────────


class AlertRuleIn(BaseModel):
    name: str
    agent_name: str
    metric: str
    operator: str = "gt"
    threshold: float
    mode: str = "absolute"
    window_size: int = 10
    enabled: bool = True
    webhook_url: Optional[str] = None


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    agent_name: Optional[str] = None
    metric: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    mode: Optional[str] = None
    window_size: Optional[int] = None
    enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
