"""CRUD for replay sandbox sessions."""

import json
import uuid
from typing import Optional

from sqlmodel import Session, col, select

from replay_models import ReplaySession
from storage import _get_engine


def create_replay_session(data: dict) -> ReplaySession:
    engine = _get_engine()
    session_obj = ReplaySession(
        id=str(uuid.uuid4()),
        trace_id=data["trace_id"],
        user_id=data["user_id"],
        name=data.get("name", "Untitled replay"),
        modifications_json=json.dumps(data.get("modifications", {})),
        notes=data.get("notes", ""),
    )
    with Session(engine) as session:
        session.add(session_obj)
        session.commit()
        session.refresh(session_obj)
    return session_obj


def list_replay_sessions(trace_id: str, user_id: str) -> list[ReplaySession]:
    engine = _get_engine()
    with Session(engine) as session:
        stmt = (
            select(ReplaySession)
            .where(ReplaySession.trace_id == trace_id, ReplaySession.user_id == user_id)
            .order_by(col(ReplaySession.created_at).desc())
        )
        return list(session.exec(stmt).all())


def get_replay_session(session_id: str, user_id: str) -> Optional[ReplaySession]:
    engine = _get_engine()
    with Session(engine) as session:
        rs = session.get(ReplaySession, session_id)
        if not rs or rs.user_id != user_id:
            return None
        return rs


def delete_replay_session(session_id: str, user_id: str) -> bool:
    engine = _get_engine()
    with Session(engine) as session:
        rs = session.get(ReplaySession, session_id)
        if not rs or rs.user_id != user_id:
            return False
        session.delete(rs)
        session.commit()
    return True
