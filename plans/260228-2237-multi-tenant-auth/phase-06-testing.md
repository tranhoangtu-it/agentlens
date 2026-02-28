# Phase 6 — Testing

## Context Links
- [conftest.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/tests/conftest.py) — test DB fixture, TestClient
- [test_api_endpoints.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/tests/test_api_endpoints.py) — existing endpoint test patterns
- [test_alert_api_endpoints.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/tests/test_alert_api_endpoints.py) — alert test patterns
- All phase files — features under test

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: Comprehensive tests for auth models/storage, auth endpoints, tenant isolation, and migration seeding

## Key Insights
- Existing tests use `pytest` + `FastAPI TestClient` + fresh SQLite DB per test (via `test_db` fixture)
- `conftest.py` replaces `storage._engine` with test engine — same pattern works for auth
- Need to register auth models in conftest so tables are created
- Tests should cover both happy path and security boundaries (cross-tenant access)

## Architecture

### Test Structure
```
server/tests/
├── conftest.py          # Updated: import auth_models for table creation, add auth fixtures
├── test_auth.py         # Auth storage + endpoints (register, login, me, api-keys)
├── test_tenant_isolation.py  # Cross-tenant access denied, tenant-scoped queries
├── test_api_endpoints.py     # Updated: add auth headers to existing tests
├── test_alert_api_endpoints.py  # Updated: add auth headers
└── ...existing tests...
```

### Test Fixtures (add to conftest.py)
```python
@pytest.fixture
def auth_user(client):
    """Register a test user and return (user_data, token, headers)."""
    res = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "display_name": "Test User",
    })
    data = res.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return data["user"], token, headers

@pytest.fixture
def auth_headers(auth_user):
    """Just the auth headers dict for convenience."""
    return auth_user[2]

@pytest.fixture
def second_user(client):
    """Second user for cross-tenant tests."""
    res = client.post("/api/auth/register", json={
        "email": "other@example.com",
        "password": "otherpass123",
        "display_name": "Other User",
    })
    data = res.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return data["user"], token, headers
```

## Related Code Files

### Files to Create
1. `server/tests/test_auth.py` — auth storage + endpoint tests (~150 lines)
2. `server/tests/test_tenant_isolation.py` — cross-tenant isolation tests (~130 lines)

### Files to Modify
1. `server/tests/conftest.py` — import auth_models, add auth fixtures
2. `server/tests/test_api_endpoints.py` — add auth headers to existing requests
3. `server/tests/test_alert_api_endpoints.py` — add auth headers to existing requests

## Implementation Steps

### 1. Update conftest.py
- Import `auth_models` so auth tables are created in test DB
- Add `auth_user`, `auth_headers`, `second_user` fixtures

### 2. Create `test_auth.py`

**Storage tests:**
- `test_create_user` — creates user with hashed password
- `test_create_user_duplicate_email` — raises or returns error
- `test_verify_password_correct` — returns True
- `test_verify_password_wrong` — returns False
- `test_create_api_key` — returns prefixed key starting with `al_`
- `test_validate_api_key_valid` — returns user
- `test_validate_api_key_invalid` — returns None

**Endpoint tests:**
- `test_register_success` — 201, returns token + user
- `test_register_duplicate_email` — 409
- `test_register_missing_fields` — 422
- `test_login_success` — 200, returns token + user
- `test_login_wrong_password` — 401
- `test_login_nonexistent_user` — 401
- `test_me_with_valid_token` — 200, returns user
- `test_me_without_token` — 401
- `test_me_with_expired_token` — 401
- `test_create_api_key_endpoint` — 201, returns full_key
- `test_list_api_keys_endpoint` — 200, shows prefixes only
- `test_delete_api_key_endpoint` — 204
- `test_api_key_auth_on_trace_ingestion` — X-API-Key header works for POST /api/traces

### 3. Create `test_tenant_isolation.py`

**Trace isolation:**
- `test_user_a_cannot_see_user_b_traces` — User A creates trace, User B GET /api/traces returns empty
- `test_user_a_cannot_get_user_b_trace_detail` — User B GET /api/traces/{id} returns 404
- `test_user_a_cannot_add_spans_to_user_b_trace` — returns 404
- `test_list_traces_filtered_by_user` — each user sees only their own
- `test_list_agents_filtered_by_user` — each user sees only their agent names

**Alert isolation:**
- `test_user_a_cannot_see_user_b_alert_rules` — filtered list
- `test_user_a_cannot_update_user_b_alert_rule` — returns 404
- `test_user_a_cannot_see_user_b_alert_events` — filtered list

**Compare isolation:**
- `test_compare_cross_tenant_traces` — returns 404 if either trace belongs to other user

**API key isolation:**
- `test_user_a_cannot_delete_user_b_api_key` — returns 404

### 4. Update existing test files
- `test_api_endpoints.py` — add `auth_headers` fixture param to all requests:
  ```python
  def test_create_and_get_trace(client, sample_trace_data, auth_headers):
      res = client.post("/api/traces", json=sample_trace_data, headers=auth_headers)
      assert res.status_code == 201
  ```
- `test_alert_api_endpoints.py` — same pattern
- Ensure all existing tests still pass with auth headers

## Todo List
- [ ] Update conftest.py with auth imports + fixtures
- [ ] Create test_auth.py with storage + endpoint tests
- [ ] Create test_tenant_isolation.py with cross-tenant tests
- [ ] Update test_api_endpoints.py to include auth headers
- [ ] Update test_alert_api_endpoints.py to include auth headers
- [ ] Run full test suite — all tests pass
- [ ] Verify coverage >= 80%

## Success Criteria
- All auth storage functions covered (create, verify, validate)
- All auth endpoints covered (register, login, me, api-keys CRUD)
- Cross-tenant access explicitly tested and rejected
- Existing tests still pass with auth headers added
- No test uses mocks for auth — real JWT/bcrypt flows
- Test suite runs in < 30 seconds

## Risk Assessment
- **Existing tests break**: All existing endpoint tests will get 401 without auth headers. Must update all tests simultaneously.
- **bcrypt speed**: bcrypt hashing is intentionally slow (~0.3s per hash). Multiple auth fixtures may slow test suite. Mitigate: reuse fixtures, use session-scoped fixture for user creation if needed.
- **Test ordering**: Tests must be independent — each gets a fresh DB via `test_db` fixture (already the case).

## Test Matrix

| Feature | Happy Path | Error Path | Security |
|---------|-----------|-----------|----------|
| Register | email+password | duplicate, missing fields | - |
| Login | correct creds | wrong password, no user | - |
| JWT | valid token | expired, malformed | - |
| API Key | valid key | invalid key, revoked | - |
| Trace isolation | own traces visible | - | other user's traces 404 |
| Alert isolation | own rules visible | - | other user's rules 404 |
| Span append | own trace OK | - | other user's trace 404 |
| Compare | own traces OK | - | cross-tenant 404 |
