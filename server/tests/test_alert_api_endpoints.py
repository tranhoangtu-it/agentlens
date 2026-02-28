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
    def test_create_rule(self, client, auth_headers):
        res = client.post("/api/alert-rules", json=_rule_data(), headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["metric"] == "cost"
        assert data["enabled"] is True

    def test_list_rules(self, client, auth_headers):
        client.post("/api/alert-rules", json=_rule_data(), headers=auth_headers)
        client.post("/api/alert-rules", json=_rule_data(metric="latency"), headers=auth_headers)
        res = client.get("/api/alert-rules", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()["rules"]) == 2

    def test_list_rules_filter_by_metric(self, client, auth_headers):
        client.post("/api/alert-rules", json=_rule_data(metric="cost"), headers=auth_headers)
        client.post("/api/alert-rules", json=_rule_data(metric="latency"), headers=auth_headers)
        res = client.get("/api/alert-rules?metric=cost", headers=auth_headers)
        assert len(res.json()["rules"]) == 1

    def test_update_rule(self, client, auth_headers):
        create_res = client.post("/api/alert-rules", json=_rule_data(), headers=auth_headers)
        rule_id = create_res.json()["id"]
        res = client.put(
            f"/api/alert-rules/{rule_id}",
            json={"name": "Updated", "threshold": 1.0},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"
        assert res.json()["threshold"] == 1.0

    def test_update_nonexistent_rule(self, client, auth_headers):
        res = client.put("/api/alert-rules/nonexistent", json={"name": "X"}, headers=auth_headers)
        assert res.status_code == 404

    def test_delete_rule(self, client, auth_headers):
        create_res = client.post("/api/alert-rules", json=_rule_data(), headers=auth_headers)
        rule_id = create_res.json()["id"]
        res = client.delete(f"/api/alert-rules/{rule_id}", headers=auth_headers)
        assert res.status_code == 204
        list_res = client.get("/api/alert-rules", headers=auth_headers)
        assert len(list_res.json()["rules"]) == 0

    def test_delete_nonexistent_rule(self, client, auth_headers):
        res = client.delete("/api/alert-rules/nonexistent", headers=auth_headers)
        assert res.status_code == 404

    def test_invalid_metric_rejected(self, client, auth_headers):
        data = _rule_data(metric="invalid_metric")
        res = client.post("/api/alert-rules", json=data, headers=auth_headers)
        assert res.status_code == 422


class TestAlertEvents:
    def test_alerts_list_empty(self, client, auth_headers):
        res = client.get("/api/alerts", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["alerts"] == []
        assert res.json()["total"] == 0

    def test_alerts_summary_empty(self, client, auth_headers):
        res = client.get("/api/alerts/summary", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["unresolved_count"] == 0


class TestAlertEvaluation:
    def test_cost_alert_fires_on_high_cost_trace(self, client, auth_headers):
        """Create a cost rule, ingest a trace exceeding threshold, verify alert fires."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="search_agent", metric="cost", threshold=0.0001,
        ), headers=auth_headers)

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
        }, headers=auth_headers)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] >= 1
        alert = res.json()["alerts"][0]
        assert alert["metric"] == "cost"
        assert alert["trace_id"] == trace_id

    def test_no_alert_when_below_threshold(self, client, auth_headers):
        """No alert should fire when trace cost is below threshold."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="search_agent", metric="cost", threshold=100.0,
        ), headers=auth_headers)

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
        }, headers=auth_headers)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] == 0

    def test_resolve_alert(self, client, auth_headers):
        """Create alert then resolve it."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="search_agent", metric="cost", threshold=0.0001,
        ), headers=auth_headers)
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
        }, headers=auth_headers)

        alerts = client.get("/api/alerts", headers=auth_headers).json()["alerts"]
        assert len(alerts) >= 1
        alert_id = alerts[0]["id"]

        res = client.patch(f"/api/alerts/{alert_id}/resolve", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["resolved"] is True

        summary = client.get("/api/alerts/summary", headers=auth_headers).json()
        assert summary["unresolved_count"] == 0

    def test_wildcard_rule_matches_any_agent(self, client, auth_headers):
        """Rule with agent_name='*' should match any agent."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="*", metric="cost", threshold=0.0001,
        ), headers=auth_headers)

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
        }, headers=auth_headers)

        res = client.get("/api/alerts", headers=auth_headers)
        assert res.json()["total"] >= 1
