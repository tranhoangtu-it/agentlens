"""Tests for alert rules and alert events API endpoints."""

import uuid


def _rule_data(agent="test_agent", metric="cost", threshold=0.5):
    return {
        "name": f"Test rule {uuid.uuid4().hex[:6]}",
        "agent_name": agent,
        "metric": metric,
        "operator": "gt",
        "threshold": threshold,
        "mode": "absolute",
        "window_size": 10,
    }


class TestAlertRulesCRUD:
    def test_create_rule(self, client):
        res = client.post("/api/alert-rules", json=_rule_data())
        assert res.status_code == 201
        data = res.json()
        assert data["metric"] == "cost"
        assert data["enabled"] is True

    def test_list_rules(self, client):
        client.post("/api/alert-rules", json=_rule_data())
        client.post("/api/alert-rules", json=_rule_data(metric="latency"))
        res = client.get("/api/alert-rules")
        assert res.status_code == 200
        assert len(res.json()["rules"]) == 2

    def test_list_rules_filter_by_metric(self, client):
        client.post("/api/alert-rules", json=_rule_data(metric="cost"))
        client.post("/api/alert-rules", json=_rule_data(metric="latency"))
        res = client.get("/api/alert-rules?metric=cost")
        assert len(res.json()["rules"]) == 1

    def test_update_rule(self, client):
        create_res = client.post("/api/alert-rules", json=_rule_data())
        rule_id = create_res.json()["id"]
        res = client.put(f"/api/alert-rules/{rule_id}", json={"name": "Updated", "threshold": 1.0})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"
        assert res.json()["threshold"] == 1.0

    def test_update_nonexistent_rule(self, client):
        res = client.put("/api/alert-rules/nonexistent", json={"name": "X"})
        assert res.status_code == 404

    def test_delete_rule(self, client):
        create_res = client.post("/api/alert-rules", json=_rule_data())
        rule_id = create_res.json()["id"]
        res = client.delete(f"/api/alert-rules/{rule_id}")
        assert res.status_code == 204
        # Verify deleted
        list_res = client.get("/api/alert-rules")
        assert len(list_res.json()["rules"]) == 0

    def test_delete_nonexistent_rule(self, client):
        res = client.delete("/api/alert-rules/nonexistent")
        assert res.status_code == 404

    def test_invalid_metric_rejected(self, client):
        data = _rule_data(metric="invalid_metric")
        res = client.post("/api/alert-rules", json=data)
        assert res.status_code == 422


class TestAlertEvents:
    def test_alerts_list_empty(self, client):
        res = client.get("/api/alerts")
        assert res.status_code == 200
        assert res.json()["alerts"] == []
        assert res.json()["total"] == 0

    def test_alerts_summary_empty(self, client):
        res = client.get("/api/alerts/summary")
        assert res.status_code == 200
        assert res.json()["unresolved_count"] == 0


class TestAlertEvaluation:
    def test_cost_alert_fires_on_high_cost_trace(self, client):
        """Create a cost rule, ingest a trace exceeding threshold, verify alert fires."""
        # Create rule: alert if cost > 0.0001
        client.post("/api/alert-rules", json=_rule_data(
            agent="search_agent", metric="cost", threshold=0.0001,
        ))

        # Ingest trace with cost
        trace_id = f"trace-{uuid.uuid4()}"
        client.post("/api/traces", json={
            "trace_id": trace_id,
            "agent_name": "search_agent",
            "spans": [{
                "span_id": f"span-{uuid.uuid4()}",
                "name": "agent_run",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": 2000,
                "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.01},
            }],
        })

        # Check alerts
        res = client.get("/api/alerts")
        assert res.json()["total"] >= 1
        alert = res.json()["alerts"][0]
        assert alert["metric"] == "cost"
        assert alert["trace_id"] == trace_id

    def test_no_alert_when_below_threshold(self, client):
        """No alert should fire when trace cost is below threshold."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="search_agent", metric="cost", threshold=100.0,
        ))

        trace_id = f"trace-{uuid.uuid4()}"
        client.post("/api/traces", json={
            "trace_id": trace_id,
            "agent_name": "search_agent",
            "spans": [{
                "span_id": f"span-{uuid.uuid4()}",
                "name": "agent_run",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": 2000,
                "cost": {"model": "gpt-4o", "input_tokens": 10, "output_tokens": 5, "usd": 0.001},
            }],
        })

        res = client.get("/api/alerts")
        assert res.json()["total"] == 0

    def test_resolve_alert(self, client):
        """Create alert then resolve it."""
        # Create rule + trigger alert
        client.post("/api/alert-rules", json=_rule_data(
            agent="search_agent", metric="cost", threshold=0.0001,
        ))
        client.post("/api/traces", json={
            "trace_id": f"trace-{uuid.uuid4()}",
            "agent_name": "search_agent",
            "spans": [{
                "span_id": f"span-{uuid.uuid4()}",
                "name": "run",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": 2000,
                "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.01},
            }],
        })

        # Get alert and resolve
        alerts = client.get("/api/alerts").json()["alerts"]
        assert len(alerts) >= 1
        alert_id = alerts[0]["id"]

        res = client.patch(f"/api/alerts/{alert_id}/resolve")
        assert res.status_code == 200
        assert res.json()["resolved"] is True

        # Summary should show 0
        summary = client.get("/api/alerts/summary").json()
        assert summary["unresolved_count"] == 0

    def test_wildcard_rule_matches_any_agent(self, client):
        """Rule with agent_name='*' should match any agent."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="*", metric="cost", threshold=0.0001,
        ))

        client.post("/api/traces", json={
            "trace_id": f"trace-{uuid.uuid4()}",
            "agent_name": "any_random_agent",
            "spans": [{
                "span_id": f"span-{uuid.uuid4()}",
                "name": "run",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": 2000,
                "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.05},
            }],
        })

        res = client.get("/api/alerts")
        assert res.json()["total"] >= 1
