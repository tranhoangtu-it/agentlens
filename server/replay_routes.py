"""API routes for replay sandbox sessions."""

import json

from fastapi import APIRouter, Depends, HTTPException

from auth_deps import get_current_user
from auth_models import User
from replay_models import ReplaySessionIn, ReplaySessionOut
from replay_storage import (
    create_replay_session, list_replay_sessions,
    get_replay_session, delete_replay_session,
)
from storage import get_trace

router = APIRouter(prefix="/api", tags=["replay"])


def _session_to_out(rs) -> ReplaySessionOut:
    return ReplaySessionOut(
        id=rs.id,
        trace_id=rs.trace_id,
        name=rs.name,
        modifications=json.loads(rs.modifications_json),
        notes=rs.notes,
        created_at=rs.created_at.isoformat(),
    )


@router.post("/replay-sessions", status_code=201)
def create_session_endpoint(body: ReplaySessionIn, user: User = Depends(get_current_user)):
    """Create a replay session with modified span inputs."""
    # Verify trace exists and belongs to user
    trace_data = get_trace(body.trace_id, user_id=user.id)
    if not trace_data:
        raise HTTPException(404, "Trace not found")

    # Validate modification span IDs exist in trace
    valid_ids = {s.id for s in trace_data["spans"]}
    invalid = [sid for sid in body.modifications if sid not in valid_ids]
    if invalid:
        raise HTTPException(422, f"Invalid span IDs: {', '.join(invalid[:5])}")

    rs = create_replay_session({
        "trace_id": body.trace_id,
        "user_id": user.id,
        "name": body.name,
        "modifications": body.modifications,
        "notes": body.notes,
    })
    return _session_to_out(rs)


@router.get("/traces/{trace_id}/replay-sessions")
def list_sessions_endpoint(trace_id: str, user: User = Depends(get_current_user)):
    """List replay sessions for a trace."""
    sessions = list_replay_sessions(trace_id, user.id)
    return {"sessions": [_session_to_out(s) for s in sessions]}


@router.get("/replay-sessions/{session_id}")
def get_session_endpoint(session_id: str, user: User = Depends(get_current_user)):
    rs = get_replay_session(session_id, user.id)
    if not rs:
        raise HTTPException(404, "Replay session not found")
    return _session_to_out(rs)


@router.delete("/replay-sessions/{session_id}", status_code=204)
def delete_session_endpoint(session_id: str, user: User = Depends(get_current_user)):
    if not delete_replay_session(session_id, user.id):
        raise HTTPException(404, "Replay session not found")
