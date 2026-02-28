"""Alert notification delivery — SSE publish and webhook fire-and-forget."""

import ipaddress
import json
import logging
import re
import socket
import threading
import urllib.parse
import urllib.request

from alert_models import AlertEvent, AlertRule
from sse import bus

logger = logging.getLogger(__name__)

# Private/loopback CIDR ranges blocked for SSRF prevention
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),    # loopback
    ipaddress.ip_network("10.0.0.0/8"),     # RFC-1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC-1918
    ipaddress.ip_network("192.168.0.0/16"), # RFC-1918
    ipaddress.ip_network("169.254.0.0/16"), # link-local
    ipaddress.ip_network("::1/128"),        # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),       # IPv6 ULA
]

_BLOCKED_HOSTNAMES = {"localhost"}


def validate_webhook_url(url: str) -> None:
    """Validate webhook URL for SSRF safety.

    Raises ValueError if the URL scheme is not http/https, the hostname
    resolves to a private/loopback address, or the hostname is blocked.
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Webhook URL must use http or https scheme, got: {parsed.scheme!r}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Webhook URL missing hostname")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Webhook URL hostname not allowed: {hostname!r}")

    # Resolve hostname to IPs and check each against blocked networks
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Webhook URL hostname could not be resolved: {hostname!r} — {exc}") from exc

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(
                    f"Webhook URL resolves to a private/internal address ({ip_str}) — not allowed"
                )


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
    """Fire-and-forget webhook POST in background thread. Never raises.

    Validates the URL for SSRF before dispatching; logs warning and skips
    if the URL fails validation.
    """
    try:
        validate_webhook_url(url)
    except ValueError as exc:
        logger.warning("Webhook URL rejected (SSRF prevention): %s — %s", url, exc)
        return

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
            logger.warning("Webhook delivery failed for %s", url)

    threading.Thread(target=_send, daemon=True).start()
