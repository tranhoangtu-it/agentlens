# Security Audit Report — AgentLens Server

**Date:** 2026-03-01
**Scope:** server/ directory (main.py, auth_jwt.py, auth_deps.py, auth_routes.py, auth_storage.py, auth_seed.py, alert_routes.py, alert_notifier.py, alert_models.py, otel_mapper.py, storage.py)
**Status:** 3 fixes applied, 86/86 tests pass

---

## Findings Summary

| # | File | Severity | Finding | Status |
|---|------|----------|---------|--------|
| 1 | main.py | HIGH | CORS wildcard `allow_origins=["*"]` | FIXED |
| 2 | auth_jwt.py | MEDIUM | No warning when JWT secret auto-generated | FIXED |
| 3 | alert_notifier.py | MEDIUM | Webhook SSRF — no URL validation | FIXED |
| 4 | auth_seed.py | MEDIUM | Default admin password warning already present | OK |
| 5 | auth_deps.py | LOW | No rate limiting on auth endpoints | DOCUMENTED |
| 6 | main.py | LOW | HTTPS not enforced | DOCUMENTED |
| 7 | otel_mapper.py | LOW | No payload size cap on span body | DOCUMENTED |
| 8 | auth_storage.py | INFO | Password hashing (bcrypt) — correct | OK |
| 9 | auth_storage.py | INFO | API key stored as SHA-256 hash — correct | OK |
| 10 | storage.py | INFO | SQL injection prevention via ORM + allowlist | OK |

---

## Fixed Issues (Applied)

### Fix 1 — CORS Wildcard (HIGH)
**File:** `server/main.py`
**Before:** `allow_origins=["*"]` — any origin can make credentialed cross-origin requests.
**After:** Reads `AGENTLENS_CORS_ORIGINS` env var (comma-separated), defaults to `http://localhost:3000,http://localhost:5173`.
```python
_cors_origins_env = os.environ.get(
    "AGENTLENS_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
```
**Production:** Set `AGENTLENS_CORS_ORIGINS=https://your-domain.com` to restrict origins.

---

### Fix 2 — JWT Secret Warning (MEDIUM)
**File:** `server/auth_jwt.py`
**Before:** Silent fallback to `secrets.token_hex(32)` — no indication in logs that sessions are ephemeral.
**After:** Logs `WARNING` when secret is auto-generated, explaining tokens are invalidated on restart.
```python
if _jwt_secret_env:
    _JWT_SECRET = _jwt_secret_env
else:
    _JWT_SECRET = secrets.token_hex(32)
    logger.warning(
        "AGENTLENS_JWT_SECRET is not set — a random secret was generated. "
        "All JWT tokens will be invalidated on server restart. ..."
    )
```
**Production:** Set `AGENTLENS_JWT_SECRET` to a long random hex string (e.g. `openssl rand -hex 32`).

---

### Fix 3 — Webhook SSRF Prevention (MEDIUM)
**File:** `server/alert_notifier.py`
**Before:** `fire_webhook(url, event)` called `urllib.request.urlopen(url)` with no validation — an attacker who can create/update alert rules could forge requests to internal services.
**After:** `validate_webhook_url(url)` runs before every dispatch:
- Scheme must be `http` or `https` — blocks `file://`, `gopher://`, etc.
- Hostname blocked list: `localhost`
- Resolves hostname via `socket.getaddrinfo`, checks all returned IPs against blocked CIDR ranges:
  - `127.0.0.0/8` (loopback)
  - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC-1918 private)
  - `169.254.0.0/16` (link-local)
  - `::1/128`, `fc00::/7` (IPv6 loopback + ULA)
- If validation fails: logs WARNING and skips delivery (no exception propagated to caller).

---

## Documented Issues (No Code Change Needed)

### Rate Limiting — LOW
**Affected:** `/api/auth/login`, `/api/auth/register`, `/api/otel/v1/traces`
**Risk:** Brute-force login, credential stuffing, ingestion spam.
**Recommendation:** Enforce at reverse proxy (nginx `limit_req`, Caddy rate_limit, or cloud WAF). Do not implement in-process for a self-hosted tool — reverse proxy is the correct layer.

---

### HTTPS Enforcement — LOW (Deployment)
**Affected:** All endpoints.
**Risk:** Credentials/tokens transmitted in plaintext over HTTP.
**Recommendation:** Terminate TLS at reverse proxy (nginx/Caddy) or cloud load balancer. The FastAPI app should run behind a proxy; mark as deployment concern in docs.

---

### OTel Payload Size — LOW
**File:** `server/main.py` — `POST /api/otel/v1/traces` accepts `body: dict`; FastAPI has no built-in body-size cap by default.
**Risk:** Very large payloads could exhaust memory.
**Recommendation:** Set `--limit-request-body` in uvicorn or add nginx `client_max_body_size`. Acceptable to handle at infra level for a self-hosted tool.

---

## Confirmed Secure (No Changes Needed)

### Password Hashing
`bcrypt` with `gensalt()` (work factor ~12) — correct. Timing-safe via `bcrypt.checkpw`.

### API Key Storage
Keys stored as `SHA-256(full_key)`. Only `key_prefix` (first 8 chars + `...`) shown in API. Full key returned only at creation time. Correct implementation.

### SQL Injection Prevention
- ORM (`SQLModel`/`SQLAlchemy`) for all queries — no raw string interpolation.
- Sort column validated against explicit allowlist in `list_traces()`.
- Date parameters parsed via `datetime.fromisoformat()` before use.

### JWT Implementation
- Algorithm pinned to `HS256` — no `alg: none` vulnerability.
- `decode_token` passes `algorithms=[_JWT_ALGORITHM]` — no algorithm confusion.
- 24-hour expiry enforced.

### Multi-Tenant Isolation
- All data queries filter by `user_id`.
- Cross-tenant access returns `None` → HTTP 404 (no information leakage via 403).

### Admin Default Password Warning
`auth_seed.py` already logs `WARNING` when `AGENTLENS_ADMIN_PASSWORD == "changeme"`.

---

## Files Modified

| File | Change | Lines Added |
|------|--------|-------------|
| `server/main.py` | CORS configurable via env | +7 |
| `server/auth_jwt.py` | JWT warning on missing secret | +10 |
| `server/alert_notifier.py` | SSRF validation + blocked networks | +55 |

## Test Results

```
86 passed in 37.53s
```

All 86 existing tests pass with no regressions.

---

## Unresolved Questions

None.
