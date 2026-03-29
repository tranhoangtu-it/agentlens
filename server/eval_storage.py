"""CRUD functions for eval criteria and eval runs."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import func
from sqlmodel import Session, col, select

from eval_models import EvalCriteria, EvalRun
from storage import _get_engine


# ── Criteria CRUD ────────────────────────────────────────────────────────────

def create_criteria(data: dict) -> EvalCriteria:
    engine = _get_engine()
    criteria = EvalCriteria(id=str(uuid.uuid4()), **data)
    with Session(engine) as session:
        session.add(criteria)
        session.commit()
        session.refresh(criteria)
    return criteria


def list_criteria(user_id: str, agent_name: Optional[str] = None) -> list[EvalCriteria]:
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(EvalCriteria).where(EvalCriteria.user_id == user_id)
        if agent_name:
            stmt = stmt.where(
                (EvalCriteria.agent_name == agent_name) | (EvalCriteria.agent_name == "*")
            )
        stmt = stmt.order_by(col(EvalCriteria.created_at).desc())
        return list(session.exec(stmt).all())


def get_criteria(criteria_id: str, user_id: str) -> Optional[EvalCriteria]:
    engine = _get_engine()
    with Session(engine) as session:
        c = session.get(EvalCriteria, criteria_id)
        if not c or c.user_id != user_id:
            return None
        return c


def update_criteria(criteria_id: str, data: dict, user_id: str) -> Optional[EvalCriteria]:
    engine = _get_engine()
    with Session(engine) as session:
        c = session.get(EvalCriteria, criteria_id)
        if not c or c.user_id != user_id:
            return None
        for key, val in data.items():
            if val is not None:
                setattr(c, key, val)
        c.updated_at = datetime.now(timezone.utc)
        session.add(c)
        session.commit()
        session.refresh(c)
    return c


def delete_criteria(criteria_id: str, user_id: str) -> bool:
    engine = _get_engine()
    with Session(engine) as session:
        c = session.get(EvalCriteria, criteria_id)
        if not c or c.user_id != user_id:
            return False
        session.delete(c)
        session.commit()
    return True


# ── Eval Runs ────────────────────────────────────────────────────────────────

def create_eval_run(data: dict) -> EvalRun:
    engine = _get_engine()
    run = EvalRun(id=str(uuid.uuid4()), **data)
    with Session(engine) as session:
        session.add(run)
        session.commit()
        session.refresh(run)
    return run


def list_eval_runs(
    user_id: str,
    criteria_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[EvalRun], int]:
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(EvalRun).where(EvalRun.user_id == user_id)
        count_stmt = select(func.count()).select_from(EvalRun).where(EvalRun.user_id == user_id)
        if criteria_id:
            stmt = stmt.where(EvalRun.criteria_id == criteria_id)
            count_stmt = count_stmt.where(EvalRun.criteria_id == criteria_id)
        if trace_id:
            stmt = stmt.where(EvalRun.trace_id == trace_id)
            count_stmt = count_stmt.where(EvalRun.trace_id == trace_id)
        stmt = stmt.order_by(col(EvalRun.created_at).desc())
        total = session.exec(count_stmt).one()
        runs = list(session.exec(stmt.offset(offset).limit(limit)).all())
        return runs, total


def get_eval_run(run_id: str, user_id: str) -> Optional[EvalRun]:
    engine = _get_engine()
    with Session(engine) as session:
        run = session.get(EvalRun, run_id)
        if not run or run.user_id != user_id:
            return None
        return run


def get_score_aggregates(
    user_id: str,
    criteria_id: Optional[str] = None,
) -> list[dict]:
    """Get average scores grouped by criteria."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = (
            select(
                EvalRun.criteria_id,
                func.avg(EvalRun.score).label("avg_score"),
                func.count().label("run_count"),
            )
            .where(EvalRun.user_id == user_id)
            .group_by(EvalRun.criteria_id)
        )
        if criteria_id:
            stmt = stmt.where(EvalRun.criteria_id == criteria_id)
        rows = session.exec(stmt).all()
        return [
            {"criteria_id": r[0], "avg_score": round(r[1], 2), "run_count": r[2]}
            for r in rows
        ]
