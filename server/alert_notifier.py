"""Alert notification delivery — SSE publish and webhook fire-and-forget."""

import json
import logging
import threading
import urllib.request

from alert_models import AlertEvent, AlertRule
from sse import bus

logger = logging.getLogger(__name__)


def publish_alert_sse(rule: AlertRule, event: AlertEvent) -> None:
    """Publish alert_fired SSE event for real-time dashboard updates."""
    bus.publish("alert_fired", {
        "alert_id": event.id,
        "rule_name": rule.name,
        "agent_name": event.agent_name,
        "metric": event.metric,
        "message": event.message,
    })


def fire_webhook(url: str, event: AlertEvent) -> None:
    """Fire-and-forget webhook POST in background thread. Never raises."""
    def _send():
        try:
            payload = json.dumps({
                "alert_id": event.id,
                "rule_id": event.rule_id,
                "trace_id": event.trace_id,
                "agent_name": event.agent_name,
                "metric": event.metric,
                "value": event.value,
                "threshold": event.threshold,
                "message": event.message,
            }).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            logger.warning("Webhook failed for %s", url)

    threading.Thread(target=_send, daemon=True).start()
