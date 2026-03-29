"""Tests for LLM-as-Judge evaluation endpoints."""

import json
from unittest.mock import patch


def _setup_key(client, auth_headers):
    """Configure API key for eval."""
    client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "openai",
        "llm_api_key": "sk-test",
        "llm_model": "gpt-4o-mini",
    })


# ── Criteria CRUD ────────────────────────────────────────────────────────────

def test_create_criteria(client, auth_headers):
    res = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "factual-accuracy",
        "description": "Is the response factually accurate?",
        "rubric": "5=perfect, 1=completely wrong",
        "score_type": "numeric",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "factual-accuracy"
    assert data["score_type"] == "numeric"
    assert data["enabled"] is True


def test_list_criteria(client, auth_headers):
    client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "helpfulness",
        "description": "Is it helpful?",
        "rubric": "pass if helpful",
        "score_type": "binary",
    })
    res = client.get("/api/eval/criteria", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["criteria"]) >= 1


def test_update_criteria(client, auth_headers):
    res = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "test-update",
        "description": "desc",
        "rubric": "rubric",
    })
    cid = res.json()["id"]
    res2 = client.put(f"/api/eval/criteria/{cid}", headers=auth_headers, json={
        "name": "updated-name",
    })
    assert res2.status_code == 200
    assert res2.json()["name"] == "updated-name"


def test_delete_criteria(client, auth_headers):
    res = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "to-delete",
        "description": "d",
        "rubric": "r",
    })
    cid = res.json()["id"]
    assert client.delete(f"/api/eval/criteria/{cid}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/eval/criteria/{cid}", headers=auth_headers).status_code == 404


def test_invalid_score_type(client, auth_headers):
    res = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "bad",
        "description": "d",
        "rubric": "r",
        "score_type": "invalid",
    })
    assert res.status_code == 422


# ── Eval execution ───────────────────────────────────────────────────────────

_MOCK_EVAL_RESPONSE = json.dumps({"score": 4.0, "reasoning": "Good output"})


@patch("eval_runner.call_llm", return_value=_MOCK_EVAL_RESPONSE)
def test_run_eval(mock_llm, client, auth_headers, sample_trace_data):
    _setup_key(client, auth_headers)
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    cres = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "quality",
        "description": "Is it good?",
        "rubric": "5=great, 1=bad",
    })
    cid = cres.json()["id"]

    res = client.post("/api/eval/run", headers=auth_headers, json={
        "criteria_id": cid,
        "trace_ids": [sample_trace_data["trace_id"]],
    })
    assert res.status_code == 201
    data = res.json()
    assert data["count"] == 1
    assert data["runs"][0]["score"] == 4.0
    assert data["runs"][0]["reasoning"] == "Good output"


def test_run_eval_no_api_key(client, auth_headers, sample_trace_data):
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    cres = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "test-nokey",
        "description": "d",
        "rubric": "r",
    })
    res = client.post("/api/eval/run", headers=auth_headers, json={
        "criteria_id": cres.json()["id"],
        "trace_ids": [sample_trace_data["trace_id"]],
    })
    assert res.status_code == 422


# ── Eval runs listing ────────────────────────────────────────────────────────

@patch("eval_runner.call_llm", return_value=_MOCK_EVAL_RESPONSE)
def test_list_runs(mock_llm, client, auth_headers, sample_trace_data):
    _setup_key(client, auth_headers)
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    cres = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "list-test",
        "description": "d",
        "rubric": "r",
    })
    client.post("/api/eval/run", headers=auth_headers, json={
        "criteria_id": cres.json()["id"],
        "trace_ids": [sample_trace_data["trace_id"]],
    })
    res = client.get("/api/eval/runs", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1


# ── Score aggregation ────────────────────────────────────────────────────────

@patch("eval_runner.call_llm", return_value=_MOCK_EVAL_RESPONSE)
def test_score_aggregates(mock_llm, client, auth_headers, sample_trace_data):
    _setup_key(client, auth_headers)
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    cres = client.post("/api/eval/criteria", headers=auth_headers, json={
        "name": "agg-test",
        "description": "d",
        "rubric": "r",
    })
    cid = cres.json()["id"]
    client.post("/api/eval/run", headers=auth_headers, json={
        "criteria_id": cid,
        "trace_ids": [sample_trace_data["trace_id"]],
    })
    res = client.get(f"/api/eval/scores?criteria_id={cid}", headers=auth_headers)
    assert res.status_code == 200
    scores = res.json()["scores"]
    assert len(scores) == 1
    assert scores[0]["avg_score"] == 4.0
