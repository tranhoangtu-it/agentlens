"""CRUD functions for alert rules and alert events."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import func
from sqlmodel import Session, col, select

from alert_models import AlertEvent, AlertRule
from storage import _get_engine


def create_alert_rule(data: dict) -> AlertRule:
    """Create a new alert rule."""
    engine = _get_engine()
    rule = AlertRule(id=str(uuid.uuid4()), **data)
    with Session(engine) as session:
        session.add(rule)
        session.commit()
        session.refresh(rule)
    return rule


def list_alert_rules(
    agent_name: Optional[str] = None,
    metric: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> list[AlertRule]:
    """List alert rules with optional filters."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(AlertRule).order_by(col(AlertRule.created_at).desc())
        if agent_name:
            stmt = stmt.where(AlertRule.agent_name == agent_name)
        if metric:
            stmt = stmt.where(AlertRule.metric == metric)
        if enabled is not None:
            stmt = stmt.where(AlertRule.enabled == enabled)
        return list(session.exec(stmt).all())


def get_alert_rule(rule_id: str) -> Optional[AlertRule]:
    """Get a single alert rule by ID."""
    engine = _get_engine()
    with Session(engine) as session:
        return session.get(AlertRule, rule_id)


def update_alert_rule(rule_id: str, data: dict) -> Optional[AlertRule]:
    """Update an existing alert rule. Returns None if not found."""
    engine = _get_engine()
    with Session(engine) as session:
        rule = session.get(AlertRule, rule_id)
        if not rule:
            return None
        for key, val in data.items():
            if val is not None:
                setattr(rule, key, val)
        rule.updated_at = datetime.now(timezone.utc)
        session.add(rule)
        session.commit()
        session.refresh(rule)
    return rule


def delete_alert_rule(rule_id: str) -> bool:
    """Delete an alert rule. Returns True if deleted."""
    engine = _get_engine()
    with Session(engine) as session:
        rule = session.get(AlertRule, rule_id)
        if not rule:
            return False
        session.delete(rule)
        session.commit()
    return True


def create_alert_event(data: dict) -> AlertEvent:
    """Create a new alert event."""
    engine = _get_engine()
    event = AlertEvent(id=str(uuid.uuid4()), **data)
    with Session(engine) as session:
        session.add(event)
        session.commit()
        session.refresh(event)
    return event


def list_alert_events(
    agent_name: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[AlertEvent], int]:
    """List alert events with optional filters. Returns (events, total)."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(AlertEvent).order_by(col(AlertEvent.created_at).desc())
        count_stmt = select(func.count()).select_from(AlertEvent)

        if agent_name:
            stmt = stmt.where(AlertEvent.agent_name == agent_name)
            count_stmt = count_stmt.where(AlertEvent.agent_name == agent_name)
        if resolved is not None:
            stmt = stmt.where(AlertEvent.resolved == resolved)
            count_stmt = count_stmt.where(AlertEvent.resolved == resolved)

        total = session.exec(count_stmt).one()
        events = list(session.exec(stmt.offset(offset).limit(limit)).all())
        return events, total


def resolve_alert_event(event_id: str) -> Optional[AlertEvent]:
    """Mark an alert event as resolved. Returns None if not found."""
    engine = _get_engine()
    with Session(engine) as session:
        event = session.get(AlertEvent, event_id)
        if not event:
            return None
        event.resolved = True
        session.add(event)
        session.commit()
        session.refresh(event)
    return event


def get_unresolved_alert_count() -> int:
    """Return count of unresolved alert events."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(func.count()).select_from(AlertEvent).where(AlertEvent.resolved == False)
        return session.exec(stmt).one()
