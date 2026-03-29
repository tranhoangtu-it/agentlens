"""Tests for replay sandbox session endpoints."""


def test_create_replay_session(client, auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    span_id = sample_trace_data["spans"][0]["span_id"]

    res = client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": sample_trace_data["trace_id"],
        "name": "Test replay",
        "modifications": {span_id: {"input": "modified search query"}},
        "notes": "Testing with different input",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test replay"
    assert data["modifications"][span_id]["input"] == "modified search query"


def test_create_replay_invalid_span(client, auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    res = client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": sample_trace_data["trace_id"],
        "modifications": {"nonexistent-span": {"input": "test"}},
    })
    assert res.status_code == 422
    assert "Invalid span IDs" in res.json()["detail"]


def test_list_replay_sessions(client, auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    tid = sample_trace_data["trace_id"]
    client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": tid, "name": "Session 1",
    })
    client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": tid, "name": "Session 2",
    })
    res = client.get(f"/api/traces/{tid}/replay-sessions", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["sessions"]) == 2


def test_get_replay_session(client, auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    create_res = client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": sample_trace_data["trace_id"], "name": "Get test",
    })
    sid = create_res.json()["id"]
    res = client.get(f"/api/replay-sessions/{sid}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Get test"


def test_delete_replay_session(client, auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    create_res = client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": sample_trace_data["trace_id"],
    })
    sid = create_res.json()["id"]
    assert client.delete(f"/api/replay-sessions/{sid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/replay-sessions/{sid}", headers=auth_headers).status_code == 404


def test_replay_tenant_isolation(client, auth_headers, second_auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    create_res = client.post("/api/replay-sessions", headers=auth_headers, json={
        "trace_id": sample_trace_data["trace_id"],
    })
    sid = create_res.json()["id"]
    # Second user can't access
    res = client.get(f"/api/replay-sessions/{sid}", headers=second_auth_headers)
    assert res.status_code == 404
