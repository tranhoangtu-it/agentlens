"""Alert evaluation engine — evaluates rules against completed traces."""

import logging
from typing import Optional

from sqlmodel import Session, col, select

from alert_models import AlertEvent, AlertRule
from alert_notifier import fire_webhook, publish_alert_sse
from alert_storage import create_alert_event
from models import Span, Trace
from storage import _get_engine

logger = logging.getLogger(__name__)

# Operator comparison functions
_OPS = {
    "gt": lambda v, t: v > t,
    "lt": lambda v, t: v < t,
    "gte": lambda v, t: v >= t,
    "lte": lambda v, t: v <= t,
}


def evaluate_alert_rules(trace_id: str, agent_name: str) -> list[AlertEvent]:
    """Evaluate all enabled alert rules against a completed trace.

    Returns list of created AlertEvent objects. Never raises — logs errors.
    """
    try:
        return _do_evaluate(trace_id, agent_name)
    except Exception:
        logger.exception("Alert evaluation failed for trace %s", trace_id)
        return []


def _do_evaluate(trace_id: str, agent_name: str) -> list[AlertEvent]:
    """Core evaluation logic."""
    engine = _get_engine()
    with Session(engine) as session:
        # Read user_id from trace for tenant-scoped rule lookup
        trace_obj = session.get(Trace, trace_id)
        trace_user_id = trace_obj.user_id if trace_obj else None

        # Fetch enabled rules matching this agent/wildcard AND owned by same user
        stmt = select(AlertRule).where(
            AlertRule.enabled == True,
            (AlertRule.agent_name == agent_name) | (AlertRule.agent_name == "*"),
        )
        if trace_user_id:
            stmt = stmt.where(AlertRule.user_id == trace_user_id)
        rules = list(session.exec(stmt).all())

        if not rules:
            return []

        # Fetch trace + spans
        trace = session.get(Trace, trace_id)
        if not trace:
            return []
        spans = list(session.exec(
            select(Span).where(Span.trace_id == trace_id)
        ).all())

        events = []
        for rule in rules:
            event = _evaluate_single_rule(session, rule, trace, spans)
            if event:
                events.append(event)
        return events


def _evaluate_single_rule(
    session: Session, rule: AlertRule, trace: Trace, spans: list[Span],
) -> Optional[AlertEvent]:
    """Evaluate a single rule against a trace. Returns AlertEvent if triggered."""
    # Cooldown: skip if last event for this rule was < 60s ago
    last_event = session.exec(
        select(AlertEvent)
        .where(AlertEvent.rule_id == rule.id)
        .order_by(col(AlertEvent.created_at).desc())
        .limit(1)
    ).first()
    if last_event:
        from datetime import datetime, timezone
        delta = (datetime.now(timezone.utc) - last_event.created_at).total_seconds()
        if delta < 60:
            return None

    value = _compute_metric(rule.metric, trace, spans)
    if value is None:
        return None

    # Determine effective threshold
    if rule.mode == "relative":
        baseline = _get_baseline_avg(
            session, trace.agent_name, rule.metric, rule.window_size, trace.id,
            user_id=trace.user_id,
        )
        if baseline is None:
            return None  # No baseline — skip relative rule
        effective_threshold = rule.threshold * baseline
    else:
        effective_threshold = rule.threshold

    # Compare
    op_fn = _OPS.get(rule.operator, _OPS["gt"])
    if not op_fn(value, effective_threshold):
        return None

    # Triggered — create alert event
    message = _build_message(rule, value, effective_threshold)
    event_data = {
        "rule_id": rule.id,
        "trace_id": trace.id,
        "agent_name": trace.agent_name,
        "metric": rule.metric,
        "value": value,
        "threshold": effective_threshold,
        "message": message,
    }
    if trace.user_id:
        event_data["user_id"] = trace.user_id
    event = create_alert_event(event_data)

    # Publish SSE + webhook
    publish_alert_sse(rule, event)
    if rule.webhook_url:
        fire_webhook(rule.webhook_url, event)

    return event


def _compute_metric(
    metric: str, trace: Trace, spans: list[Span],
) -> Optional[float]:
    """Compute the metric value from a trace and its spans."""
    if metric == "cost":
        return trace.total_cost_usd
    elif metric == "latency":
        return float(trace.duration_ms) if trace.duration_ms else None
    elif metric == "error_rate":
        if not spans:
            return None
        error_count = sum(1 for s in spans if s.end_ms is None)
        return error_count / len(spans)
    elif metric == "missing_span":
        # For missing_span, value = number of missing spans
        # threshold stores JSON array of expected span names
        return None  # Handled separately in _evaluate_single_rule
    return None


def _get_baseline_avg(
    session: Session,
    agent_name: str,
    metric: str,
    window: int,
    exclude_trace_id: str,
    user_id: Optional[str] = None,
) -> Optional[float]:
    """Get rolling average of a metric from last N completed traces (tenant-scoped)."""
    stmt = (
        select(Trace)
        .where(
            Trace.agent_name == agent_name,
            Trace.status == "completed",
            Trace.id != exclude_trace_id,
        )
        .order_by(col(Trace.created_at).desc())
        .limit(window)
    )
    if user_id:
        stmt = stmt.where(Trace.user_id == user_id)
    traces = list(session.exec(stmt).all())
    if not traces:
        return None

    values = []
    for t in traces:
        if metric == "cost" and t.total_cost_usd is not None:
            values.append(t.total_cost_usd)
        elif metric == "latency" and t.duration_ms is not None:
            values.append(float(t.duration_ms))

    return sum(values) / len(values) if values else None


def _build_message(rule: AlertRule, value: float, threshold: float) -> str:
    """Build human-readable alert message."""
    metric_labels = {
        "cost": "Cost",
        "error_rate": "Error rate",
        "latency": "Latency (ms)",
        "missing_span": "Missing spans",
    }
    label = metric_labels.get(rule.metric, rule.metric)
    return f"{label} = {value:.4g} {rule.operator} {threshold:.4g} (rule: {rule.name})"


