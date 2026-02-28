"""Tests for auth endpoints: register, login, me, api-keys."""


def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "display_name": "New User",
    })
    assert res.status_code == 201
    data = res.json()
    assert "token" in data
    assert data["email"] == "new@example.com"
    assert "user_id" in data


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={
        "email": "dup@example.com", "password": "password123",
    })
    res = client.post("/api/auth/register", json={
        "email": "dup@example.com", "password": "password456",
    })
    assert res.status_code == 409


def test_register_short_password(client):
    res = client.post("/api/auth/register", json={
        "email": "short@example.com", "password": "abc",
    })
    assert res.status_code == 422


def test_login_success(client):
    client.post("/api/auth/register", json={
        "email": "login@example.com", "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "email": "login@example.com", "password": "password123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["email"] == "login@example.com"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "wrong@example.com", "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "email": "wrong@example.com", "password": "badpassword",
    })
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/api/auth/login", json={
        "email": "ghost@example.com", "password": "password123",
    })
    assert res.status_code == 401


def test_me_with_valid_token(client, auth_headers):
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert "user_id" in data


def test_me_without_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_with_invalid_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401


def test_create_api_key(client, auth_headers):
    res = client.post("/api/auth/api-keys?name=test-key", headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["key"].startswith("al_")
    assert data["name"] == "test-key"
    assert "key_prefix" in data


def test_list_api_keys(client, auth_headers):
    client.post("/api/auth/api-keys?name=key1", headers=auth_headers)
    client.post("/api/auth/api-keys?name=key2", headers=auth_headers)
    res = client.get("/api/auth/api-keys", headers=auth_headers)
    assert res.status_code == 200
    keys = res.json()["keys"]
    assert len(keys) == 2
    # Full key never returned in list
    for k in keys:
        assert "key" not in k or k.get("key") is None


def test_delete_api_key(client, auth_headers):
    create_res = client.post("/api/auth/api-keys?name=del", headers=auth_headers)
    key_id = create_res.json()["id"]
    res = client.delete(f"/api/auth/api-keys/{key_id}", headers=auth_headers)
    assert res.status_code == 204
    # Verify deleted
    list_res = client.get("/api/auth/api-keys", headers=auth_headers)
    assert all(k["id"] != key_id for k in list_res.json()["keys"])


def test_api_key_auth_on_trace_ingestion(client, auth_headers, sample_trace_data):
    """Create API key then use it with X-API-Key header to ingest a trace."""
    create_res = client.post("/api/auth/api-keys?name=sdk", headers=auth_headers)
    full_key = create_res.json()["key"]

    res = client.post(
        "/api/traces",
        json=sample_trace_data,
        headers={"X-API-Key": full_key},
    )
    assert res.status_code == 201
    assert res.json()["trace_id"] == sample_trace_data["trace_id"]
