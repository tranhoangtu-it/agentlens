"""Tests for alert_notifier.py: validate_webhook_url, publish_alert_sse, fire_webhook."""

import sys
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from alert_notifier import fire_webhook, publish_alert_sse, validate_webhook_url
from alert_models import AlertEvent, AlertRule


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_rule(name="Test Rule", webhook_url=None):
    return AlertRule(
        id="rule-1",
        name=name,
        agent_name="test_agent",
        metric="cost",
        operator="gt",
        threshold=0.5,
        mode="absolute",
        window_size=10,
        enabled=True,
        webhook_url=webhook_url,
    )


def _make_event(rule_id="rule-1", trace_id="trace-1"):
    return AlertEvent(
        id="event-1",
        rule_id=rule_id,
        trace_id=trace_id,
        agent_name="test_agent",
        metric="cost",
        value=1.0,
        threshold=0.5,
        message="Cost = 1.0 gt 0.5 (rule: Test Rule)",
    )


# ── validate_webhook_url ───────────────────────────────────────────────────────

class TestValidateWebhookUrl:
    def test_valid_https_url_passes(self):
        """Public HTTPS URL resolving to a public IP should pass."""
        # Patch getaddrinfo to return a public IP
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            # Should not raise
            validate_webhook_url("https://example.com/webhook")

    def test_valid_http_url_passes(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0))
            ]
            validate_webhook_url("http://example.com/hook")

    def test_non_http_scheme_rejected(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_webhook_url("ftp://example.com/hook")

    def test_missing_scheme_rejected(self):
        with pytest.raises(ValueError):
            validate_webhook_url("example.com/hook")

    def test_localhost_hostname_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_webhook_url("http://localhost/hook")

    def test_loopback_ip_blocked(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))
            ]
            with pytest.raises(ValueError, match="private/internal"):
                validate_webhook_url("http://internal.example.com/hook")

    def test_private_10_network_blocked(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))
            ]
            with pytest.raises(ValueError, match="private/internal"):
                validate_webhook_url("http://internal.example.com/hook")

    def test_private_172_network_blocked(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("172.20.0.1", 0))
            ]
            with pytest.raises(ValueError, match="private/internal"):
                validate_webhook_url("http://internal.example.com/hook")

    def test_private_192_168_network_blocked(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ]
            with pytest.raises(ValueError, match="private/internal"):
                validate_webhook_url("http://internal.example.com/hook")

    def test_link_local_network_blocked(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.0.1", 0))
            ]
            with pytest.raises(ValueError, match="private/internal"):
                validate_webhook_url("http://link-local.example.com/hook")

    def test_ipv6_loopback_blocked(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0))
            ]
            with pytest.raises(ValueError, match="private/internal"):
                validate_webhook_url("http://ipv6-loopback.example.com/hook")

    def test_dns_resolution_failure_raises(self):
        with patch("socket.getaddrinfo") as mock_gai:
            mock_gai.side_effect = socket.gaierror("Name not resolved")
            with pytest.raises(ValueError, match="could not be resolved"):
                validate_webhook_url("http://nonexistent.invalid/hook")

    def test_missing_hostname_rejected(self):
        with pytest.raises(ValueError, match="missing hostname"):
            validate_webhook_url("http:///path")

    def test_invalid_ip_in_getaddrinfo_result_skipped(self):
        """If getaddrinfo returns a non-parseable IP string, it is skipped (no crash)."""
        with patch("socket.getaddrinfo") as mock_gai:
            # Return a result where sockaddr[0] is not a valid IP — should be skipped
            # Then a valid public IP so validation passes
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("not_a_valid_ip", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
            ]
            # Should not raise — invalid IP entry skipped, public IP passes
            validate_webhook_url("https://example.com/webhook")


# ── publish_alert_sse ─────────────────────────────────────────────────────────

class TestPublishAlertSse:
    def test_publishes_to_sse_bus(self):
        """publish_alert_sse calls bus.publish with correct event type and data."""
        rule = _make_rule()
        event = _make_event()

        with patch("alert_notifier.bus") as mock_bus:
            publish_alert_sse(rule, event)

        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        event_type = call_args[0][0]
        data = call_args[0][1]

        assert event_type == "alert_fired"
        assert data["alert_id"] == "event-1"
        assert data["rule_name"] == "Test Rule"
        assert data["agent_name"] == "test_agent"
        assert data["metric"] == "cost"
        assert "message" in data

    def test_publishes_message_content(self):
        rule = _make_rule(name="Latency Rule")
        event = _make_event()
        event.message = "Latency = 500 gt 200"

        with patch("alert_notifier.bus") as mock_bus:
            publish_alert_sse(rule, event)

        data = mock_bus.publish.call_args[0][1]
        assert data["message"] == "Latency = 500 gt 200"


# ── fire_webhook ──────────────────────────────────────────────────────────────

class TestFireWebhook:
    def test_rejected_url_logs_warning_and_skips(self, caplog):
        """SSRF-rejected URL: logs warning, no thread spawned."""
        import logging
        event = _make_event()

        with caplog.at_level(logging.WARNING, logger="alert_notifier"):
            fire_webhook("http://localhost/hook", event)

        assert any("rejected" in r.message.lower() or "SSRF" in r.message for r in caplog.records)

    def test_valid_url_spawns_thread_and_posts(self):
        """Valid URL: urllib.request.urlopen called with POST request."""
        event = _make_event()

        with patch("socket.getaddrinfo") as mock_gai, \
             patch("urllib.request.urlopen") as mock_open:
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            fire_webhook("https://example.com/webhook", event)

            # Give background thread time to complete
            import time
            time.sleep(0.1)

        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        assert req.get_method() == "POST"
        assert req.get_header("Content-type") == "application/json"

    def test_webhook_delivery_failure_logged(self, caplog):
        """urllib raises: warning logged, no exception propagated."""
        import logging
        event = _make_event()

        with patch("socket.getaddrinfo") as mock_gai, \
             patch("urllib.request.urlopen") as mock_open, \
             caplog.at_level(logging.WARNING, logger="alert_notifier"):
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            mock_open.side_effect = Exception("Connection refused")
            fire_webhook("https://example.com/webhook", event)

            import time
            time.sleep(0.1)

        assert any("failed" in r.message.lower() for r in caplog.records)

    def test_webhook_payload_contains_event_fields(self):
        """Payload sent to webhook includes all required AlertEvent fields."""
        import json
        event = _make_event()
        captured_requests = []

        def fake_urlopen(req, timeout=None):
            captured_requests.append(req)

        with patch("socket.getaddrinfo") as mock_gai, \
             patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mock_gai.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            fire_webhook("https://example.com/webhook", event)

            import time
            time.sleep(0.1)

        assert len(captured_requests) == 1
        payload = json.loads(captured_requests[0].data.decode())
        assert payload["alert_id"] == "event-1"
        assert payload["rule_id"] == "rule-1"
        assert payload["trace_id"] == "trace-1"
        assert payload["agent_name"] == "test_agent"
        assert payload["metric"] == "cost"
        assert "value" in payload
        assert "threshold" in payload
        assert "message" in payload
