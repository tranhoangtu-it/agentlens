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


class TestAlertRouteValidation:
    def test_invalid_operator_rejected_on_create(self, client, auth_headers):
        """Invalid operator rejected with 422."""
        data = _rule_data()
        data["operator"] = "invalid_op"
        res = client.post("/api/alert-rules", json=data, headers=auth_headers)
        assert res.status_code == 422

    def test_invalid_mode_rejected_on_create(self, client, auth_headers):
        """Invalid mode rejected with 422."""
        data = _rule_data()
        data["mode"] = "invalid_mode"
        res = client.post("/api/alert-rules", json=data, headers=auth_headers)
        assert res.status_code == 422

    def test_invalid_operator_rejected_on_update(self, client, auth_headers):
        """Invalid operator in update rejected with 422."""
        create_res = client.post("/api/alert-rules", json=_rule_data(), headers=auth_headers)
        rule_id = create_res.json()["id"]
        res = client.put(
            f"/api/alert-rules/{rule_id}",
            json={"operator": "bad_op"},
            headers=auth_headers,
        )
        assert res.status_code == 422

    def test_resolve_nonexistent_alert_returns_404(self, client, auth_headers):
        """Resolving a non-existent alert event returns 404."""
        res = client.patch("/api/alerts/nonexistent-id/resolve", headers=auth_headers)
        assert res.status_code == 404

    def test_list_alerts_filtered_by_agent(self, client, auth_headers):
        """List alert events can be filtered by agent_name."""
        # Create rule and fire an alert
        client.post("/api/alert-rules", json=_rule_data(
            agent="filter_agent", metric="cost", threshold=0.0001,
        ), headers=auth_headers)
        client.post("/api/traces", json={
            "trace_id": f"trace-{uuid.uuid4()}",
            "agent_name": "filter_agent",
            "spans": [{
                "span_id": f"span-{uuid.uuid4()}",
                "name": "run",
                "type": "agent_run",
                "start_ms": 100,
                "end_ms": 200,
                "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.05},
            }],
        }, headers=auth_headers)

        # Filter by agent_name
        res = client.get("/api/alerts?agent_name=filter_agent", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["total"] >= 1
        for alert in res.json()["alerts"]:
            assert alert["agent_name"] == "filter_agent"

    def test_list_alerts_filtered_by_resolved(self, client, auth_headers):
        """List alert events can be filtered by resolved=true."""
        client.post("/api/alert-rules", json=_rule_data(
            agent="res_agent", metric="cost", threshold=0.0001,
        ), headers=auth_headers)
        client.post("/api/traces", json={
            "trace_id": f"trace-{uuid.uuid4()}",
            "agent_name": "res_agent",
            "spans": [{
                "span_id": f"span-{uuid.uuid4()}",
                "name": "run",
                "type": "agent_run",
                "start_ms": 100,
                "end_ms": 200,
                "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.05},
            }],
        }, headers=auth_headers)

        alerts = client.get("/api/alerts", headers=auth_headers).json()["alerts"]
        assert len(alerts) >= 1
        alert_id = alerts[0]["id"]

        # Resolve it
        client.patch(f"/api/alerts/{alert_id}/resolve", headers=auth_headers)

        # Filter resolved=true
        res = client.get("/api/alerts?resolved=true", headers=auth_headers)
        assert res.status_code == 200
        resolved_alerts = res.json()["alerts"]
        assert all(a["resolved"] is True for a in resolved_alerts)

    def test_list_alert_rules_filter_by_agent(self, client, auth_headers):
        """List rules can be filtered by agent_name."""
        client.post("/api/alert-rules", json=_rule_data(agent="specific_agent"), headers=auth_headers)
        client.post("/api/alert-rules", json=_rule_data(agent="other_agent"), headers=auth_headers)
        res = client.get("/api/alert-rules?agent_name=specific_agent", headers=auth_headers)
        assert res.status_code == 200
        rules = res.json()["rules"]
        assert all(r["agent_name"] == "specific_agent" for r in rules)

    def test_list_alert_rules_filter_by_enabled(self, client, auth_headers):
        """List rules can be filtered by enabled status."""
        create_res = client.post("/api/alert-rules", json=_rule_data(), headers=auth_headers)
        rule_id = create_res.json()["id"]
        client.put(f"/api/alert-rules/{rule_id}", json={"enabled": False}, headers=auth_headers)

        res = client.get("/api/alert-rules?enabled=false", headers=auth_headers)
        rules = res.json()["rules"]
        assert len(rules) == 1
        assert rules[0]["enabled"] is False


class TestAlertStorageCrossTenantAccess:
    """Tests for alert_storage user_id ownership checks (lines 48-55, 138)."""

    def test_get_alert_rule_wrong_user_returns_none(self, test_db):
        """get_alert_rule returns None when rule belongs to different user."""
        from alert_storage import create_alert_rule, get_alert_rule

        rule = create_alert_rule({
            "name": "Private Rule",
            "agent_name": "agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 1.0,
            "mode": "absolute",
            "window_size": 10,
            "user_id": "user-aaa",
        })

        # Access with different user_id
        result = get_alert_rule(rule.id, user_id="user-bbb")
        assert result is None

    def test_get_alert_rule_correct_user_returns_rule(self, test_db):
        """get_alert_rule returns rule when user_id matches."""
        from alert_storage import create_alert_rule, get_alert_rule

        rule = create_alert_rule({
            "name": "Owned Rule",
            "agent_name": "agent",
            "metric": "cost",
            "operator": "gt",
            "threshold": 1.0,
            "mode": "absolute",
            "window_size": 10,
            "user_id": "user-ccc",
        })

        result = get_alert_rule(rule.id, user_id="user-ccc")
        assert result is not None
        assert result.id == rule.id

    def test_get_alert_rule_not_found_returns_none(self, test_db):
        """get_alert_rule returns None when rule doesn't exist."""
        from alert_storage import get_alert_rule

        result = get_alert_rule("nonexistent-id")
        assert result is None

    def test_resolve_alert_event_wrong_user_returns_none(self, test_db):
        """resolve_alert_event returns None when event belongs to different user."""
        from alert_storage import create_alert_event, resolve_alert_event
        import uuid

        event = create_alert_event({
            "rule_id": str(uuid.uuid4()),
            "trace_id": str(uuid.uuid4()),
            "agent_name": "agent",
            "metric": "cost",
            "value": 1.0,
            "threshold": 0.5,
            "message": "test",
            "user_id": "user-xxx",
        })

        result = resolve_alert_event(event.id, user_id="user-yyy")
        assert result is None

    def test_list_alert_events_filter_by_agent_and_resolved(self, test_db):
        """list_alert_events filters by agent_name and resolved simultaneously."""
        from alert_storage import create_alert_event, list_alert_events
        import uuid

        trace_id = str(uuid.uuid4())
        rule_id = str(uuid.uuid4())

        ev1 = create_alert_event({
            "rule_id": rule_id,
            "trace_id": trace_id,
            "agent_name": "target_agent",
            "metric": "cost",
            "value": 1.0,
            "threshold": 0.5,
            "message": "msg1",
        })
        ev2 = create_alert_event({
            "rule_id": rule_id,
            "trace_id": trace_id,
            "agent_name": "other_agent",
            "metric": "cost",
            "value": 1.0,
            "threshold": 0.5,
            "message": "msg2",
        })

        events, total = list_alert_events(agent_name="target_agent", resolved=False)
        assert total >= 1
        assert all(e.agent_name == "target_agent" for e in events)
