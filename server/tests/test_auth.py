"""Tests for auth endpoints: register, login, me, api-keys, auth_deps."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


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


# ── auth_deps: get_optional_user ───────────────────────────────────────────────

def test_get_optional_user_returns_user_with_valid_token(client, auth_headers):
    """get_optional_user returns User when valid Bearer token supplied."""
    from auth_deps import get_optional_user
    from fastapi import Request

    # Use an endpoint that internally calls get_optional_user by hitting /api/auth/me
    # Instead test directly via mocking Request
    from auth_jwt import create_token
    from auth_storage import get_user_by_email

    # Register a user via API so they're in DB
    client.post("/api/auth/register", json={
        "email": "optional@example.com",
        "password": "password123",
    })
    user = get_user_by_email("optional@example.com")
    token = create_token(user.id, user.email)

    mock_request = MagicMock()
    mock_request.headers.get = lambda key, default="": (
        f"Bearer {token}" if key == "Authorization" else default
    )

    result = get_optional_user(mock_request)
    assert result is not None
    assert result.email == "optional@example.com"


def test_get_optional_user_returns_none_without_auth(client):
    """get_optional_user returns None when no auth header is provided."""
    from auth_deps import get_optional_user

    mock_request = MagicMock()
    mock_request.headers.get = lambda key, default="": default

    result = get_optional_user(mock_request)
    assert result is None


def test_get_optional_user_returns_none_with_invalid_token(client):
    """get_optional_user returns None for invalid JWT — no 401 raised."""
    from auth_deps import get_optional_user

    mock_request = MagicMock()
    mock_request.headers.get = lambda key, default="": (
        "Bearer invalid.jwt.token" if key == "Authorization" else default
    )

    result = get_optional_user(mock_request)
    assert result is None


def test_get_current_user_with_apikey_prefix(client, auth_headers):
    """ApiKey <key> Authorization header is accepted (Bearer variant)."""
    create_res = client.post("/api/auth/api-keys?name=apikey-prefix-test", headers=auth_headers)
    full_key = create_res.json()["key"]

    res = client.post(
        "/api/traces",
        json={
            "trace_id": "apikey-prefix-trace",
            "agent_name": "test_agent",
            "spans": [],
        },
        headers={"Authorization": f"ApiKey {full_key}"},
    )
    assert res.status_code == 201


def test_get_current_user_missing_auth_returns_401(client):
    """Requests with no auth header receive 401."""
    res = client.get("/api/traces")
    assert res.status_code == 401


# ── auth_jwt: decode_token edge cases ─────────────────────────────────────────

def test_decode_expired_token_returns_none():
    """Expired JWT token should return None from decode_token."""
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta
    from auth_jwt import _JWT_SECRET, _JWT_ALGORITHM, decode_token

    expired_payload = {
        "sub": "user-123",
        "email": "x@example.com",
        "iat": datetime.now(timezone.utc) - timedelta(hours=48),
        "exp": datetime.now(timezone.utc) - timedelta(hours=24),
    }
    expired_token = pyjwt.encode(expired_payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    result = decode_token(expired_token)
    assert result is None


def test_decode_token_wrong_secret_returns_none():
    """Token signed with wrong secret returns None."""
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta
    from auth_jwt import _JWT_ALGORITHM, decode_token

    payload = {
        "sub": "user-123",
        "email": "x@example.com",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    bad_token = pyjwt.encode(payload, "wrong-secret", algorithm=_JWT_ALGORITHM)
    result = decode_token(bad_token)
    assert result is None


def test_decode_valid_token_returns_payload():
    """Valid token should decode and return payload dict."""
    from auth_jwt import create_token, decode_token

    token = create_token("user-abc", "valid@example.com")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-abc"
    assert payload["email"] == "valid@example.com"


def test_get_current_user_valid_jwt_but_user_deleted(client):
    """Valid JWT for a deleted/non-existent user returns 401 User not found."""
    from auth_jwt import create_token

    # Create token for a user_id that doesn't exist in DB
    token = create_token("nonexistent-user-id", "ghost@example.com")

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "not found" in res.json()["detail"].lower()


def test_get_current_user_apikey_prefix_invalid_key_returns_401(client):
    """ApiKey <invalid> Authorization header returns 401 Invalid API key."""
    res = client.get("/api/auth/me", headers={"Authorization": "ApiKey invalid_key_value"})
    assert res.status_code == 401


def test_get_current_user_x_api_key_header_invalid_returns_401(client):
    """X-API-Key header with invalid key returns 401."""
    res = client.get("/api/auth/me", headers={"X-API-Key": "invalid_key_value"})
    assert res.status_code == 401


def test_jwt_secret_warning_when_not_set(monkeypatch, caplog):
    """auth_jwt logs warning when AGENTLENS_JWT_SECRET is not set."""
    import logging
    import importlib

    monkeypatch.delenv("AGENTLENS_JWT_SECRET", raising=False)

    with caplog.at_level(logging.WARNING, logger="auth_jwt"):
        import auth_jwt
        importlib.reload(auth_jwt)

    warning_msgs = [r.message for r in caplog.records if "JWT_SECRET" in r.message]
    assert len(warning_msgs) >= 1

    # Restore
    importlib.reload(auth_jwt)


def test_jwt_secret_used_when_env_set(monkeypatch):
    """auth_jwt uses AGENTLENS_JWT_SECRET env var when set (line 16)."""
    import importlib

    monkeypatch.setenv("AGENTLENS_JWT_SECRET", "my-test-secret-key-for-testing-only-32chars")

    import auth_jwt
    importlib.reload(auth_jwt)

    assert auth_jwt._JWT_SECRET == "my-test-secret-key-for-testing-only-32chars"

    # Restore
    monkeypatch.delenv("AGENTLENS_JWT_SECRET")
    importlib.reload(auth_jwt)
