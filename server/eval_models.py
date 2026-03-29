"""SQLModel tables and Pydantic schemas for LLM-as-Judge evaluations."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


class EvalCriteria(SQLModel, table=True):
    __tablename__ = "eval_criteria"
    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    name: str
    description: str
    rubric: str
    score_type: str = Field(default="numeric")  # "numeric" (1-5) | "binary" (pass/fail)
    agent_name: str = Field(default="*")        # filter: which agents, "*" = all
    auto_eval: bool = Field(default=False)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_eval_criteria_user_agent", "user_id", "agent_name"),
    )


class EvalRun(SQLModel, table=True):
    __tablename__ = "eval_run"
    id: str = Field(primary_key=True)
    criteria_id: str = Field(index=True)
    trace_id: str = Field(index=True)
    user_id: str = Field(index=True)
    score: float
    reasoning: str
    llm_provider: str
    llm_model: str
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_eval_run_criteria_trace", "criteria_id", "trace_id"),
        Index("ix_eval_run_user_created", "user_id", "created_at"),
    )


# ── Request schemas ──────────────────────────────────────────────────────────

class EvalCriteriaIn(BaseModel):
    name: str
    description: str
    rubric: str
    score_type: str = "numeric"
    agent_name: str = "*"
    auto_eval: bool = False
    enabled: bool = True


class EvalCriteriaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rubric: Optional[str] = None
    score_type: Optional[str] = None
    agent_name: Optional[str] = None
    auto_eval: Optional[bool] = None
    enabled: Optional[bool] = None


class EvalRunRequest(BaseModel):
    criteria_id: str
    trace_ids: list[str]
    provider: Optional[str] = None
    model: Optional[str] = None
