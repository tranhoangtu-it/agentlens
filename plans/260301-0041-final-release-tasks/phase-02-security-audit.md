# Phase 2: Security Audit

## Context Links
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Auth: `server/auth_*.py` (5 files)
- Routes: `server/main.py`, `server/alert_routes.py`, `server/auth_routes.py`
- Storage: `server/storage.py`, `server/alert_storage.py`

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 3h
- Systematic security review against OWASP Top 10, auth hardening, input validation

## Key Insights from Codebase Review

### Current Security Posture (Good)
- bcrypt password hashing (auth_storage.py:21)
- SHA-256 API key hashing — never stores plaintext (auth_storage.py:61)
- JWT HS256 with 24h expiry (auth_jwt.py)
- Tenant isolation: user_id on Trace, AlertRule, AlertEvent — cross-tenant returns 404
- SQL injection prevention: SQLModel parameterized queries throughout
- Sort column whitelist in list_traces (storage.py:122)
- Date validation before query (main.py:161-167)

### Identified Concerns
1. **CORS allow_origins=["*"]** (main.py:43) — allows any origin
2. **JWT secret auto-generated** if not set (auth_jwt.py:10) — changes on restart, invalidating all tokens
3. **No rate limiting** on login/register endpoints
4. **Default admin password "changeme"** (auth_seed.py:15) — warning logged but not enforced
5. **Error messages** may leak info (e.g., "Email already registered" in register)
6. **No HTTPS enforcement** — JWT tokens sent over plain HTTP
7. **Webhook URL not validated** — could be used for SSRF (alert_models.py:28)
8. **auth_seed.py uses raw SQL** `UPDATE {table}` — table names are hardcoded strings, not injectable, but pattern is risky
9. **No request body size limit** beyond FastAPI defaults
10. **No password complexity** beyond 8-char minimum

## Requirements

### Functional
- Document all findings with severity (Critical/High/Medium/Low/Info)
- Fix Critical and High issues
- Document Medium/Low for future consideration

### Non-functional
- No breaking API changes
- Fixes must pass all existing tests

## Architecture — Audit Checklist

### A1: Broken Access Control
- [x] Tenant isolation verified (user_id checks on all queries)
- [x] API key scoped to user
- [ ] **Check:** Can user A's JWT be used to access user B's data? (should be covered by tests)
- [ ] **Check:** OTel ingestion endpoint auth — currently requires auth

### A2: Cryptographic Failures
- [x] bcrypt for passwords
- [x] SHA-256 for API keys
- [ ] **Issue:** JWT secret auto-generated — MEDIUM risk
- [ ] **Issue:** No HTTPS enforcement — relies on deployment

### A3: Injection
- [x] SQLModel parameterized queries
- [x] Sort column whitelist
- [ ] **Check:** `_migrate_orphan_data` uses f-string but table names are hardcoded constants
- [ ] **Check:** OTel mapper input validation

### A5: Security Misconfiguration
- [ ] **Issue:** CORS wildcard — HIGH for production deployments
- [ ] **Issue:** No rate limiting — MEDIUM

### A7: Identification and Authentication Failures
- [ ] **Issue:** No login rate limiting — brute force possible — MEDIUM
- [ ] **Issue:** "Email already registered" user enumeration — LOW
- [ ] **Issue:** Default admin password — MEDIUM

### A10: Server-Side Request Forgery (SSRF)
- [ ] **Issue:** Webhook URL not validated — MEDIUM (fire_webhook accepts any URL)

## Implementation Steps

### Step 1: Create security audit report
Write findings to `plans/reports/planner-260301-0041-security-audit-findings.md`

### Step 2: Fix Critical/High issues

#### Fix 1: CORS configuration (HIGH)
```python
# main.py — read allowed origins from env, default to localhost
_CORS_ORIGINS = os.environ.get("AGENTLENS_CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Fix 2: Warn if JWT secret not set (MEDIUM → make explicit)
```python
# auth_jwt.py — log warning if auto-generated
_env_secret = os.environ.get("AGENTLENS_JWT_SECRET")
if not _env_secret:
    logger.warning("AGENTLENS_JWT_SECRET not set — using random secret (tokens invalidated on restart)")
_JWT_SECRET = _env_secret or secrets.token_hex(32)
```

#### Fix 3: Webhook URL validation (MEDIUM)
```python
# alert_routes.py — validate webhook_url if provided
from urllib.parse import urlparse

def _validate_webhook_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    # Block private IPs (basic SSRF prevention)
    hostname = parsed.hostname or ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return False
    if hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
        return False
    return True
```

#### Fix 4: Rate limiting documentation
- Document that production deployments should use a reverse proxy (nginx/Caddy) with rate limiting
- Add to deployment-guide.md

### Step 3: Document remaining findings
- User enumeration on register (LOW) — trade-off: UX vs security
- No HTTPS enforcement (deployment concern, not app-level)
- Password complexity (8 char minimum is adequate for self-hosted)
- Request body size (FastAPI default 1MB is fine)

## Todo List

- [ ] Review all auth endpoints for access control
- [ ] Review all storage functions for SQL injection
- [ ] Review CORS configuration
- [ ] Review JWT implementation
- [ ] Review webhook URL handling
- [ ] Review error messages for information leakage
- [ ] Fix CORS to use env-configurable origins
- [ ] Add JWT secret warning log
- [ ] Add webhook URL validation
- [ ] Update deployment-guide.md with security recommendations
- [ ] Write security audit report
- [ ] Run all tests to confirm no regressions

## Success Criteria
- All Critical/High findings fixed
- Security audit report written with all findings
- All existing tests still pass
- No new dependencies added

## Risk Assessment
- CORS change could break existing setups → make env-configurable with "*" still available
- Webhook validation could break existing rules with internal URLs → document the change

## Security Considerations
- This IS the security phase — all findings documented and prioritized
- Focus on defense-in-depth, not just perimeter
