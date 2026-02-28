"""Tests for tenant isolation — user A cannot see user B's data."""

import uuid


def _make_trace(base_id=None):
    """Helper to generate unique trace data."""
    base_id = base_id or str(uuid.uuid4())
    return {
        "trace_id": f"trace-{base_id}",
        "agent_name": "test_agent",
        "spans": [{
            "span_id": f"span-{base_id}",
            "name": "root",
            "type": "agent_run",
            "start_ms": 1000,
            "end_ms": 5000,
            "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.01},
        }],
    }


# ── Trace isolation ──────────────────────────────────────────────────────────


def test_user_cannot_see_other_user_traces(client, auth_headers, second_auth_headers):
    """User A creates trace, User B list returns empty."""
    trace = _make_trace()
    client.post("/api/traces", json=trace, headers=auth_headers)

    # User B sees nothing
    res = client.get("/api/traces", headers=second_auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_user_cannot_get_other_user_trace_detail(client, auth_headers, second_auth_headers):
    """User B GET /api/traces/{id} returns 404 for User A's trace."""
    trace = _make_trace()
    client.post("/api/traces", json=trace, headers=auth_headers)

    res = client.get(f"/api/traces/{trace['trace_id']}", headers=second_auth_headers)
    assert res.status_code == 404


def test_user_cannot_add_spans_to_other_user_trace(client, auth_headers, second_auth_headers):
    """User B cannot append spans to User A's trace."""
    trace = _make_trace()
    client.post("/api/traces", json=trace, headers=auth_headers)

    res = client.post(
        f"/api/traces/{trace['trace_id']}/spans",
        json={"spans": [{"span_id": "extra-1", "name": "hack", "type": "tool_call", "start_ms": 100, "end_ms": 200}]},
        headers=second_auth_headers,
    )
    assert res.status_code == 404


def test_list_traces_filtered_by_user(client, auth_headers, second_auth_headers):
    """Each user sees only their own traces."""
    t1 = _make_trace()
    t2 = _make_trace()
    client.post("/api/traces", json=t1, headers=auth_headers)
    client.post("/api/traces", json=t2, headers=second_auth_headers)

    res_a = client.get("/api/traces", headers=auth_headers)
    res_b = client.get("/api/traces", headers=second_auth_headers)
    assert res_a.json()["total"] == 1
    assert res_b.json()["total"] == 1
    assert res_a.json()["traces"][0]["id"] == t1["trace_id"]
    assert res_b.json()["traces"][0]["id"] == t2["trace_id"]


def test_list_agents_filtered_by_user(client, auth_headers, second_auth_headers):
    """Each user sees only their agent names."""
    t1 = _make_trace()
    t1["agent_name"] = "agent_a"
    t2 = _make_trace()
    t2["agent_name"] = "agent_b"
    client.post("/api/traces", json=t1, headers=auth_headers)
    client.post("/api/traces", json=t2, headers=second_auth_headers)

    res_a = client.get("/api/agents", headers=auth_headers)
    res_b = client.get("/api/agents", headers=second_auth_headers)
    assert res_a.json()["agents"] == ["agent_a"]
    assert res_b.json()["agents"] == ["agent_b"]


# ── Compare isolation ────────────────────────────────────────────────────────


def test_compare_cross_tenant_traces(client, auth_headers, second_auth_headers):
    """Cannot compare traces across tenants."""
    t1 = _make_trace()
    t2 = _make_trace()
    client.post("/api/traces", json=t1, headers=auth_headers)
    client.post("/api/traces", json=t2, headers=second_auth_headers)

    # User A tries to compare own trace with User B's trace
    res = client.get(
        f"/api/traces/compare?left={t1['trace_id']}&right={t2['trace_id']}",
        headers=auth_headers,
    )
    assert res.status_code == 404


# ── Alert rule isolation ─────────────────────────────────────────────────────


def test_user_cannot_see_other_user_alert_rules(client, auth_headers, second_auth_headers):
    """User B cannot list User A's alert rules."""
    client.post("/api/alert-rules", json={
        "name": "user_a_rule", "agent_name": "*", "metric": "cost",
        "threshold": 1.0,
    }, headers=auth_headers)

    res = client.get("/api/alert-rules", headers=second_auth_headers)
    assert res.json()["rules"] == []


def test_user_cannot_update_other_user_alert_rule(client, auth_headers, second_auth_headers):
    """User B cannot update User A's alert rule."""
    create_res = client.post("/api/alert-rules", json={
        "name": "rule_a", "agent_name": "*", "metric": "cost", "threshold": 1.0,
    }, headers=auth_headers)
    rule_id = create_res.json()["id"]

    res = client.put(
        f"/api/alert-rules/{rule_id}",
        json={"name": "hacked"},
        headers=second_auth_headers,
    )
    assert res.status_code == 404


def test_user_cannot_delete_other_user_alert_rule(client, auth_headers, second_auth_headers):
    """User B cannot delete User A's alert rule."""
    create_res = client.post("/api/alert-rules", json={
        "name": "rule_del", "agent_name": "*", "metric": "cost", "threshold": 1.0,
    }, headers=auth_headers)
    rule_id = create_res.json()["id"]

    res = client.delete(f"/api/alert-rules/{rule_id}", headers=second_auth_headers)
    assert res.status_code == 404


# ── API key isolation ────────────────────────────────────────────────────────


def test_user_cannot_delete_other_user_api_key(client, auth_headers, second_auth_headers):
    """User B cannot delete User A's API key."""
    create_res = client.post("/api/auth/api-keys?name=mine", headers=auth_headers)
    key_id = create_res.json()["id"]

    res = client.delete(f"/api/auth/api-keys/{key_id}", headers=second_auth_headers)
    assert res.status_code == 404


# ── Unauthenticated access ──────────────────────────────────────────────────


def test_unauthenticated_trace_list(client):
    """No auth → 401."""
    res = client.get("/api/traces")
    assert res.status_code == 401


def test_unauthenticated_trace_ingestion(client, sample_trace_data):
    """No auth → 401."""
    res = client.post("/api/traces", json=sample_trace_data)
    assert res.status_code == 401


def test_health_is_public(client):
    """Health endpoint remains public."""
    res = client.get("/api/health")
    assert res.status_code == 200
