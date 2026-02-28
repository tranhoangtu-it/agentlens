"""FastAPI router for alert rules and alert events endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_deps import get_current_user
from auth_models import User
from alert_models import AlertRuleIn, AlertRuleUpdate
from alert_storage import (
    create_alert_rule,
    delete_alert_rule,
    get_unresolved_alert_count,
    list_alert_events,
    list_alert_rules,
    resolve_alert_event,
    update_alert_rule,
)

router = APIRouter(prefix="/api", tags=["alerts"])

# Valid values for validation
_VALID_METRICS = {"cost", "error_rate", "latency", "missing_span"}
_VALID_OPERATORS = {"gt", "lt", "gte", "lte"}
_VALID_MODES = {"absolute", "relative"}


def _validate_rule(data: dict) -> None:
    """Validate alert rule fields."""
    if data.get("metric") and data["metric"] not in _VALID_METRICS:
        raise HTTPException(422, f"Invalid metric: {data['metric']}")
    if data.get("operator") and data["operator"] not in _VALID_OPERATORS:
        raise HTTPException(422, f"Invalid operator: {data['operator']}")
    if data.get("mode") and data["mode"] not in _VALID_MODES:
        raise HTTPException(422, f"Invalid mode: {data['mode']}")


# ── Alert Rules CRUD ─────────────────────────────────────────────────────────


@router.post("/alert-rules", status_code=201)
def create_rule(body: AlertRuleIn, user: User = Depends(get_current_user)):
    data = body.model_dump()
    data["user_id"] = user.id
    _validate_rule(data)
    rule = create_alert_rule(data)
    return rule


@router.get("/alert-rules")
def list_rules(
    agent_name: Optional[str] = Query(None),
    metric: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    user: User = Depends(get_current_user),
):
    rules = list_alert_rules(agent_name=agent_name, metric=metric, enabled=enabled, user_id=user.id)
    return {"rules": rules}


@router.put("/alert-rules/{rule_id}")
def update_rule(rule_id: str, body: AlertRuleUpdate, user: User = Depends(get_current_user)):
    data = body.model_dump(exclude_unset=True)
    _validate_rule(data)
    rule = update_alert_rule(rule_id, data, user_id=user.id)
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    return rule


@router.delete("/alert-rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, user: User = Depends(get_current_user)):
    if not delete_alert_rule(rule_id, user_id=user.id):
        raise HTTPException(404, "Alert rule not found")


# ── Alert Events ─────────────────────────────────────────────────────────────


@router.get("/alerts")
def list_alerts(
    agent_name: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    events, total = list_alert_events(
        agent_name=agent_name, resolved=resolved, limit=limit, offset=offset, user_id=user.id,
    )
    return {"alerts": events, "total": total, "limit": limit, "offset": offset}


@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, user: User = Depends(get_current_user)):
    event = resolve_alert_event(alert_id, user_id=user.id)
    if not event:
        raise HTTPException(404, "Alert event not found")
    return event


@router.get("/alerts/summary")
def alerts_summary(user: User = Depends(get_current_user)):
    count = get_unresolved_alert_count(user_id=user.id)
    return {"unresolved_count": count}
