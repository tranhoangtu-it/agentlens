"""Tests for prompt template versioning endpoints."""

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


def create_template(client, headers, name="my-prompt"):
    res = client.post("/api/prompts", json={"name": name}, headers=headers)
    assert res.status_code == 201
    return res.json()


def add_version(client, headers, prompt_id, content, variables=None, metadata=None):
    body = {"content": content}
    if variables is not None:
        body["variables"] = variables
    if metadata is not None:
        body["metadata"] = metadata
    res = client.post(f"/api/prompts/{prompt_id}/versions", json=body, headers=headers)
    assert res.status_code == 201
    return res.json()


# ── Tests ────────────────────────────────────────────────────────────────────


def test_create_prompt(client, auth_headers):
    """Creating a prompt returns the new template with version 0."""
    data = create_template(client, auth_headers, name="summariser")
    assert data["name"] == "summariser"
    assert data["latest_version"] == 0
    assert "id" in data


def test_list_prompts(client, auth_headers):
    """Listed prompts contain all created templates for the user."""
    create_template(client, auth_headers, name="prompt-a")
    create_template(client, auth_headers, name="prompt-b")

    res = client.get("/api/prompts", headers=auth_headers)
    assert res.status_code == 200
    names = [p["name"] for p in res.json()["prompts"]]
    assert "prompt-a" in names
    assert "prompt-b" in names


def test_add_version_increments(client, auth_headers):
    """Each new version increments the version counter starting from 1."""
    template = create_template(client, auth_headers)
    prompt_id = template["id"]

    v1 = add_version(client, auth_headers, prompt_id, "Hello {{name}}", variables=["name"])
    assert v1["version"] == 1

    v2 = add_version(client, auth_headers, prompt_id, "Hi {{name}}", variables=["name"])
    assert v2["version"] == 2

    # Template's latest_version should reflect the last version
    res = client.get(f"/api/prompts/{prompt_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["latest_version"] == 2


def test_get_version(client, auth_headers):
    """Retrieving a specific version returns correct content."""
    template = create_template(client, auth_headers)
    prompt_id = template["id"]

    add_version(client, auth_headers, prompt_id, "Version one content")
    add_version(client, auth_headers, prompt_id, "Version two content")

    res = client.get(f"/api/prompts/{prompt_id}/versions/1", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["content"] == "Version one content"
    assert res.json()["version"] == 1

    res2 = client.get(f"/api/prompts/{prompt_id}/versions/2", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["content"] == "Version two content"


def test_diff_versions(client, auth_headers):
    """Diff endpoint returns a non-empty unified diff string."""
    template = create_template(client, auth_headers)
    prompt_id = template["id"]

    add_version(client, auth_headers, prompt_id, "Line A\nLine B\nLine C\n")
    add_version(client, auth_headers, prompt_id, "Line A\nLine B modified\nLine C\n")

    res = client.get(f"/api/prompts/{prompt_id}/diff?v1=1&v2=2", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["v1"] == 1
    assert data["v2"] == 2
    assert "diff" in data
    assert "-Line B\n" in data["diff"]
    assert "+Line B modified\n" in data["diff"]


def test_prompt_tenant_isolation(client, auth_headers, second_auth_headers):
    """User A's prompts are not accessible to User B."""
    template = create_template(client, auth_headers, name="secret-prompt")
    prompt_id = template["id"]
    add_version(client, auth_headers, prompt_id, "Sensitive content")

    # User B cannot see user A's prompt list entry
    res = client.get("/api/prompts", headers=second_auth_headers)
    assert res.status_code == 200
    ids = [p["id"] for p in res.json()["prompts"]]
    assert prompt_id not in ids

    # User B cannot fetch user A's template directly
    res2 = client.get(f"/api/prompts/{prompt_id}", headers=second_auth_headers)
    assert res2.status_code == 404

    # User B cannot read user A's versions
    res3 = client.get(f"/api/prompts/{prompt_id}/versions/1", headers=second_auth_headers)
    assert res3.status_code == 404

    # User B cannot diff user A's versions
    res4 = client.get(f"/api/prompts/{prompt_id}/diff?v1=1&v2=2", headers=second_auth_headers)
    assert res4.status_code == 404
