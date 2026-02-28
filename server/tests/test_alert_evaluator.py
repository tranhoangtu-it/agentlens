"""Tests for alert_evaluator.py: _compute_metric, _get_baseline_avg, _build_message, cooldown."""

import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from alert_evaluator import (
    _build_message,
    _compute_metric,
    _get_baseline_avg,
    _do_evaluate,
    evaluate_alert_rules,
)
from alert_models import AlertEvent, AlertRule
from models import Span, Trace


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_trace(agent_name="agent", cost=None, duration_ms=None, status="completed", user_id=None):
    t = Trace(
        id=str(uuid.uuid4()),
        agent_name=agent_name,
        status=status,
        total_cost_usd=cost,
        duration_ms=duration_ms,
    )
    if user_id:
        t.user_id = user_id
    return t


def _make_span(trace_id, name="op", end_ms=1000):
    return Span(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        name=name,
        type="tool_call",
        start_ms=0,
        end_ms=end_ms,
    )


def _make_rule(**kwargs):
    defaults = dict(
        id=str(uuid.uuid4()),
        name="Test Rule",
        agent_name="agent",
        metric="cost",
        operator="gt",
        threshold=0.5,
        mode="absolute",
        window_size=10,
        enabled=True,
    )
    defaults.update(kwargs)
    return AlertRule(**defaults)


# ── _compute_metric ────────────────────────────────────────────────────────────

class TestComputeMetric:
    def test_cost_metric_returns_total_cost(self):
        trace = _make_trace(cost=1.23)
        result = _compute_metric("cost", trace, [])
        assert result == 1.23

    def test_cost_metric_none_when_no_cost(self):
        trace = _make_trace(cost=None)
        result = _compute_metric("cost", trace, [])
        assert result is None

    def test_latency_metric_returns_duration(self):
        trace = _make_trace(duration_ms=500)
        result = _compute_metric("latency", trace, [])
        assert result == 500.0

    def test_latency_metric_none_when_no_duration(self):
        trace = _make_trace(duration_ms=None)
        result = _compute_metric("latency", trace, [])
        assert result is None

    def test_error_rate_all_successful(self):
        trace = _make_trace()
        spans = [_make_span(trace.id, end_ms=100) for _ in range(4)]
        result = _compute_metric("error_rate", trace, spans)
        assert result == 0.0

    def test_error_rate_all_errors(self):
        trace = _make_trace()
        spans = [_make_span(trace.id, end_ms=None) for _ in range(3)]
        result = _compute_metric("error_rate", trace, spans)
        assert result == 1.0

    def test_error_rate_partial_errors(self):
        trace = _make_trace()
        good = _make_span(trace.id, end_ms=100)
        bad = _make_span(trace.id, end_ms=None)
        result = _compute_metric("error_rate", trace, [good, bad])
        assert result == 0.5

    def test_error_rate_no_spans_returns_none(self):
        trace = _make_trace()
        result = _compute_metric("error_rate", trace, [])
        assert result is None

    def test_missing_span_metric_returns_none(self):
        """missing_span metric is handled separately — compute returns None."""
        trace = _make_trace()
        result = _compute_metric("missing_span", trace, [])
        assert result is None

    def test_unknown_metric_returns_none(self):
        trace = _make_trace()
        result = _compute_metric("unknown_metric", trace, [])
        assert result is None


# ── _do_evaluate: trace-not-found path (line 60) ──────────────────────────────

class TestDoEvaluateEdgeCases:
    def test_trace_deleted_between_rule_check_and_fetch(self, test_db):
        """If trace exists for rule lookup but disappears before second get, return []."""
        from storage import create_trace
        from alert_storage import create_alert_rule

        # Create a trace and matching rule
        import uuid as _uuid
        trace_id = str(_uuid.uuid4())
        agent_name = "del_agent"

        # First create trace so _do_evaluate finds it for user_id lookup
        trace = create_trace(trace_id, agent_name, [
            {"span_id": str(_uuid.uuid4()), "name": "op", "type": "tool_call",
             "start_ms": 100, "end_ms": 200, "cost_usd": 1.0},
        ])

        create_alert_rule({
            "name": "Del Rule",
            "agent_name": agent_name,
            "metric": "cost",
            "operator": "gt",
            "threshold": 0.001,
            "mode": "absolute",
            "window_size": 10,
        })

        # Delete the trace between steps — patch session.get to return None on second call
        from sqlmodel import Session as _Session
        original_get = _Session.get
        call_count = {"n": 0}

        def patched_get(self, model, ident, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:  # second call to session.get is for trace fetch
                return None
            return original_get(self, model, ident, **kwargs)

        with patch.object(_Session, "get", patched_get):
            result = evaluate_alert_rules(trace_id, agent_name)

        assert result == []

    def test_metric_returns_none_skips_rule(self, test_db):
        """When _compute_metric returns None, rule is skipped (line 92)."""
        from storage import create_trace
        from alert_storage import create_alert_rule
        from alert_evaluator import _do_evaluate
        import uuid as _uuid

        trace_id = str(_uuid.uuid4())
        # Create trace with NO cost (total_cost_usd=None)
        trace = create_trace(trace_id, "nc_agent", [
            {"span_id": str(_uuid.uuid4()), "name": "op", "type": "tool_call",
             "start_ms": 100, "end_ms": 200},
        ])

        create_alert_rule({
            "name": "NC Rule",
            "agent_name": "nc_agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 0.001,
            "mode": "absolute",
            "window_size": 10,
        })

        result = _do_evaluate(trace_id, "nc_agent")
        # cost metric returns None when total_cost_usd is None → rule skipped
        assert result == []

    def test_cooldown_prevents_alert_within_60s(self, test_db):
        """Cooldown check: if last event was < 60s ago, return None (lines 87-88)."""
        from datetime import datetime, timezone
        from sqlmodel import Session
        from storage import create_trace, _get_engine
        from alert_storage import create_alert_rule, create_alert_event
        from alert_evaluator import _evaluate_single_rule
        import uuid as _uuid

        engine = _get_engine()
        agent_name = "cd2_agent"
        trace_id = str(_uuid.uuid4())
        trace = create_trace(trace_id, agent_name, [
            {"span_id": str(_uuid.uuid4()), "name": "op", "type": "tool_call",
             "start_ms": 100, "end_ms": 200,
             "cost": {"model": "gpt-4o", "input_tokens": 50, "output_tokens": 20, "usd": 1.0}},
        ])

        rule = create_alert_rule({
            "name": "CD2 Rule",
            "agent_name": agent_name,
            "metric": "cost",
            "operator": "gt",
            "threshold": 0.001,
            "mode": "absolute",
            "window_size": 10,
        })

        from models import Trace as TraceModel, Span as SpanModel
        from sqlmodel import select as _select
        from unittest.mock import patch as _patch

        # Use a fixed naive "now" — 5 seconds after the event was created
        # Both times are naive so subtraction works, delta = 5 < 60 → cooldown
        fixed_naive_event_time = datetime(2026, 1, 1, 12, 0, 0)  # naive
        fixed_naive_now = datetime(2026, 1, 1, 12, 0, 5)  # 5s later

        recent_event = AlertEvent(
            id=str(_uuid.uuid4()),
            rule_id=rule.id,
            trace_id=trace_id,
            agent_name=agent_name,
            metric="cost",
            value=1.0,
            threshold=0.001,
            message="prior",
            created_at=fixed_naive_event_time,
        )
        with Session(engine) as session:
            session.add(recent_event)
            session.commit()

        class _FakeDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_naive_now  # 5s after event: delta=5 < 60 → cooldown fires

        with Session(engine) as session:
            trace_obj = session.get(TraceModel, trace_id)
            spans_obj = list(session.exec(
                _select(SpanModel).where(SpanModel.trace_id == trace_id)
            ).all())

            with _patch("datetime.datetime", _FakeDatetime):
                result = _evaluate_single_rule(session, rule, trace_obj, spans_obj)

        assert result is None  # skipped due to cooldown (delta=5 < 60)


# ── _get_baseline_avg ─────────────────────────────────────────────────────────

class TestGetBaselineAvg:
    def test_returns_none_when_no_traces(self, test_db):
        from sqlmodel import Session
        from storage import _get_engine
        engine = _get_engine()
        with Session(engine) as session:
            result = _get_baseline_avg(session, "agent", "cost", 10, "exclude-me")
        assert result is None

    def test_cost_baseline_computed(self, test_db):
        from sqlmodel import Session
        from storage import _get_engine
        engine = _get_engine()

        # Insert two completed traces with cost
        t1 = _make_trace(agent_name="agent", cost=1.0, status="completed")
        t2 = _make_trace(agent_name="agent", cost=3.0, status="completed")
        with Session(engine) as session:
            session.add(t1)
            session.add(t2)
            session.commit()

        with Session(engine) as session:
            result = _get_baseline_avg(session, "agent", "cost", 10, "nonexistent")
        assert abs(result - 2.0) < 1e-9

    def test_latency_baseline_computed(self, test_db):
        from sqlmodel import Session
        from storage import _get_engine
        engine = _get_engine()

        t1 = _make_trace(agent_name="agent", duration_ms=100, status="completed")
        t2 = _make_trace(agent_name="agent", duration_ms=300, status="completed")
        with Session(engine) as session:
            session.add(t1)
            session.add(t2)
            session.commit()

        with Session(engine) as session:
            result = _get_baseline_avg(session, "agent", "latency", 10, "nonexistent")
        assert abs(result - 200.0) < 1e-9

    def test_excludes_current_trace(self, test_db):
        from sqlmodel import Session
        from storage import _get_engine
        engine = _get_engine()

        t1 = _make_trace(agent_name="agent", cost=10.0, status="completed")
        t2 = _make_trace(agent_name="agent", cost=2.0, status="completed")
        with Session(engine) as session:
            session.add(t1)
            session.add(t2)
            session.commit()
            t1_id = t1.id

        with Session(engine) as session:
            result = _get_baseline_avg(session, "agent", "cost", 10, t1_id)
        # Only t2 remains: avg = 2.0
        assert abs(result - 2.0) < 1e-9

    def test_window_limits_traces(self, test_db):
        from sqlmodel import Session
        from storage import _get_engine
        engine = _get_engine()

        # Insert 5 traces; window=2 should only use last 2
        traces = [_make_trace(agent_name="agent", cost=float(i), status="completed")
                  for i in range(1, 6)]
        with Session(engine) as session:
            for t in traces:
                session.add(t)
            session.commit()

        with Session(engine) as session:
            result = _get_baseline_avg(session, "agent", "cost", 2, "none")
        # Window=2 → last 2 traces by created_at desc → values 5 and 4
        assert result is not None

    def test_returns_none_when_no_cost_values(self, test_db):
        """Traces exist but cost is None — baseline should be None."""
        from sqlmodel import Session
        from storage import _get_engine
        engine = _get_engine()

        t1 = _make_trace(agent_name="agent", cost=None, status="completed")
        with Session(engine) as session:
            session.add(t1)
            session.commit()

        with Session(engine) as session:
            result = _get_baseline_avg(session, "agent", "cost", 10, "none")
        assert result is None


# ── _build_message ─────────────────────────────────────────────────────────────

class TestBuildMessage:
    def test_cost_message(self):
        rule = _make_rule(metric="cost", operator="gt", name="Cost Rule")
        msg = _build_message(rule, 1.5, 0.5)
        assert "Cost" in msg
        assert "gt" in msg
        assert "Cost Rule" in msg
        assert "1.5" in msg or "1.500" in msg

    def test_error_rate_message(self):
        rule = _make_rule(metric="error_rate", operator="gte", name="Error Rule")
        msg = _build_message(rule, 0.8, 0.5)
        assert "Error rate" in msg
        assert "gte" in msg

    def test_latency_message(self):
        rule = _make_rule(metric="latency", operator="lte", name="Latency Rule")
        msg = _build_message(rule, 200.0, 100.0)
        assert "Latency" in msg
        assert "lte" in msg

    def test_missing_span_message(self):
        rule = _make_rule(metric="missing_span", operator="gt", name="MS Rule")
        msg = _build_message(rule, 3.0, 0.0)
        assert "Missing" in msg or "missing" in msg

    def test_unknown_metric_uses_raw_name(self):
        rule = _make_rule(metric="custom_metric", operator="gt", name="Custom Rule")
        msg = _build_message(rule, 5.0, 3.0)
        assert "custom_metric" in msg


# ── evaluate_alert_rules (integration) ────────────────────────────────────────

class TestEvaluateAlertRules:
    def _ingest_trace(self, client, auth_headers, agent_name, cost_usd):
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        client.post("/api/traces", json={
            "trace_id": trace_id,
            "agent_name": agent_name,
            "spans": [{
                "span_id": span_id,
                "name": "run",
                "type": "agent_run",
                "start_ms": 100,
                "end_ms": 1100,
                "cost": {
                    "model": "gpt-4o",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "usd": cost_usd,
                },
            }],
        }, headers=auth_headers)
        return trace_id

    def test_evaluate_rules_no_exception_on_bad_trace(self, test_db):
        """evaluate_alert_rules logs and returns [] for unknown trace_id."""
        result = evaluate_alert_rules("nonexistent-trace", "agent")
        assert result == []

    def test_cost_alert_fires(self, client, auth_headers):
        """Absolute cost rule fires when trace cost exceeds threshold."""
        client.post("/api/alert-rules", json={
            "name": "Cost Alert",
            "agent_name": "eval_agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 0.001,
            "mode": "absolute",
            "window_size": 10,
        }, headers=auth_headers)

        self._ingest_trace(client, auth_headers, "eval_agent", 0.05)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] >= 1

    def test_latency_alert_fires(self, client, auth_headers):
        """Absolute latency rule fires when trace duration exceeds threshold."""
        client.post("/api/alert-rules", json={
            "name": "Latency Alert",
            "agent_name": "lat_agent",
            "metric": "latency",
            "operator": "gt",
            "threshold": 100,
            "mode": "absolute",
            "window_size": 10,
        }, headers=auth_headers)

        # Ingest trace with 1000ms duration (start=0, end=1000)
        self._ingest_trace(client, auth_headers, "lat_agent", 0.001)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] >= 1

    def test_cooldown_prevents_duplicate_alert(self, client, auth_headers):
        """Second alert within 60s cooldown should not fire duplicate."""
        client.post("/api/alert-rules", json={
            "name": "Cooldown Rule",
            "agent_name": "cool_agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 0.0001,
            "mode": "absolute",
            "window_size": 10,
        }, headers=auth_headers)

        # First trace fires alert
        self._ingest_trace(client, auth_headers, "cool_agent", 0.05)
        count1 = client.get("/api/alerts", headers=auth_headers).json()["total"]

        # Second trace within cooldown — no new alert
        self._ingest_trace(client, auth_headers, "cool_agent", 0.05)
        count2 = client.get("/api/alerts", headers=auth_headers).json()["total"]

        assert count2 == count1  # No additional alert due to cooldown

    def test_relative_mode_no_baseline(self, client, auth_headers):
        """Relative rule with no baseline history should not fire."""
        client.post("/api/alert-rules", json={
            "name": "Relative Rule",
            "agent_name": "rel_agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 2.0,
            "mode": "relative",
            "window_size": 5,
        }, headers=auth_headers)

        # First trace — no baseline exists, rule should skip
        self._ingest_trace(client, auth_headers, "rel_agent", 0.05)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] == 0

    def test_relative_mode_fires_when_exceeds_baseline(self, client, auth_headers):
        """Relative rule fires when current value > threshold * baseline."""
        import time
        client.post("/api/alert-rules", json={
            "name": "Relative Cost Rule",
            "agent_name": "rb_agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 1.5,  # fire if value > 1.5 * baseline
            "mode": "relative",
            "window_size": 5,
        }, headers=auth_headers)

        # Ingest 3 baseline traces at low cost
        for _ in range(3):
            self._ingest_trace(client, auth_headers, "rb_agent", 0.01)

        # Reset cooldown by patching — or ingest a massive spike
        # Spike trace with very high cost
        self._ingest_trace(client, auth_headers, "rb_agent", 1.0)

        res = client.get("/api/alerts", headers=auth_headers)
        # Alert should fire (1.0 > 1.5 * 0.01 = 0.015)
        assert res.json()["total"] >= 1

    def test_lte_operator(self, client, auth_headers):
        """lte operator fires when value <= threshold."""
        client.post("/api/alert-rules", json={
            "name": "Low Cost Rule",
            "agent_name": "lte_agent",
            "metric": "cost",
            "operator": "lte",
            "threshold": 1.0,  # fire if cost <= 1.0
            "mode": "absolute",
            "window_size": 10,
        }, headers=auth_headers)

        self._ingest_trace(client, auth_headers, "lte_agent", 0.5)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] >= 1

    def test_gte_operator(self, client, auth_headers):
        """gte operator fires when value >= threshold."""
        client.post("/api/alert-rules", json={
            "name": "High Latency Rule",
            "agent_name": "gte_agent",
            "metric": "latency",
            "operator": "gte",
            "threshold": 1000,
            "mode": "absolute",
            "window_size": 10,
        }, headers=auth_headers)

        self._ingest_trace(client, auth_headers, "gte_agent", 0.001)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] >= 1

    def test_disabled_rule_does_not_fire(self, client, auth_headers):
        """Disabled rules are ignored during evaluation."""
        res = client.post("/api/alert-rules", json={
            "name": "Disabled Rule",
            "agent_name": "dis_agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 0.0001,
            "mode": "absolute",
            "window_size": 10,
        }, headers=auth_headers)
        rule_id = res.json()["id"]

        # Disable the rule
        client.put(f"/api/alert-rules/{rule_id}",
                   json={"enabled": False}, headers=auth_headers)

        self._ingest_trace(client, auth_headers, "dis_agent", 0.05)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] == 0

    def test_evaluate_with_webhook_url(self, client, auth_headers):
        """Rule with webhook_url calls fire_webhook (mocked to prevent network)."""
        with patch("alert_evaluator.fire_webhook") as mock_fw, \
             patch("alert_evaluator.publish_alert_sse"):
            client.post("/api/alert-rules", json={
                "name": "Webhook Rule",
                "agent_name": "wh_agent",
                "metric": "cost",
                "operator": "gt",
                "threshold": 0.0001,
                "mode": "absolute",
                "window_size": 10,
                "webhook_url": "https://example.com/hook",
            }, headers=auth_headers)

            self._ingest_trace(client, auth_headers, "wh_agent", 0.05)

        # fire_webhook should have been called once
        assert mock_fw.called

    def test_error_rate_alert_fires(self, client, auth_headers):
        """Error rate rule fires when some spans have end_ms=None (errored).

        Trace must have status='completed' to trigger evaluation, so we use
        add_spans endpoint to complete the trace after ingestion with one
        completed span. We call directly on alert_evaluator instead to avoid
        the status='completed' gating in main.py.
        """
        from alert_evaluator import evaluate_alert_rules
        from alert_storage import create_alert_rule

        import uuid as _uuid
        rule_data = {
            "name": "Error Rate Rule",
            "agent_name": "err_agent",
            "metric": "error_rate",
            "operator": "gt",
            "threshold": 0.0,
            "mode": "absolute",
            "window_size": 10,
        }
        res = client.post("/api/alert-rules", json=rule_data, headers=auth_headers)
        assert res.status_code == 201

        # Ingest a completed trace with a span that has no end_ms (errored)
        # Trick: ingest via storage directly so we can set status=completed
        from storage import create_trace
        from auth_storage import get_user_by_email
        # Get user_id from auth
        me = client.get("/api/auth/me", headers=auth_headers).json()
        user_id = me["user_id"]

        trace_id = str(_uuid.uuid4())
        # Create spans: one good, one bad (end_ms=None simulates error)
        trace = create_trace(trace_id, "err_agent", [
            {"span_id": str(_uuid.uuid4()), "name": "ok", "type": "tool_call",
             "start_ms": 100, "end_ms": 200},
            {"span_id": str(_uuid.uuid4()), "name": "err", "type": "tool_call",
             "start_ms": 200, "end_ms": None},
        ], user_id=user_id)

        # Manually trigger evaluation (trace status is "running" due to missing end_ms)
        # Override status in DB for testing
        from storage import _get_engine
        from sqlmodel import Session
        from models import Trace as TraceModel
        with Session(_get_engine()) as session:
            t = session.get(TraceModel, trace_id)
            if t:
                t.status = "completed"
                session.add(t)
                session.commit()

        events = evaluate_alert_rules(trace_id, "err_agent")
        assert len(events) >= 1
