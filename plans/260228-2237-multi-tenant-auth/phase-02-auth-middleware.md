# Phase 2 — Auth Middleware & Endpoints

## Context Links
- [main.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/main.py) — FastAPI app, CORS, route registration
- [alert_routes.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/alert_routes.py) — APIRouter pattern reference
- [Phase 1](phase-01-auth-models-and-storage.md) — models + storage dependency

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: JWT token generation/validation, API key validation, FastAPI dependency injection, auth endpoints (register, login, me, api-keys)

## Key Insights
- FastAPI `Depends()` pattern is cleanest for auth — inject `current_user` into route functions
- Two auth modes: JWT (dashboard) and API key (SDK ingestion)
- Health endpoint (`/api/health`) and static files must remain public
- Auth should be opt-in per route (not global middleware) to avoid breaking health/static
- `PyJWT` encode/decode with HS256 is sufficient for self-hosted

## Architecture

### JWT Flow
```
Login → POST /api/auth/login
       → verify email + password
       → return { access_token, token_type: "bearer", user: {...} }

Dashboard → Authorization: Bearer <jwt>
           → decode JWT → extract user_id → load User → inject as current_user
```

### API Key Flow
```
SDK → X-API-Key: al_xxxxxxxxxxxx
    → SHA-256 hash key → look up ApiKey → load User → inject as current_user
```

### Dependency Resolution
```python
def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> User:
    # 1. Try JWT from Authorization: Bearer <token>
    # 2. Try API key from X-API-Key header
    # 3. Raise 401 if neither valid
```

## Related Code Files

### Files to Create
1. `server/auth_jwt.py` — JWT encode/decode helpers (~50 lines)
2. `server/auth_deps.py` — FastAPI dependency: `get_current_user`, `get_optional_user` (~60 lines)
3. `server/auth_routes.py` — APIRouter with register/login/me/api-keys endpoints (~120 lines)

### Files to Modify
1. `server/main.py` — import and register `auth_router`, tighten CORS origins

## Implementation Steps

1. **Create `server/auth_jwt.py`**
   ```python
   JWT_SECRET = os.environ.get("AGENTLENS_JWT_SECRET", secrets.token_hex(32))
   JWT_ALGORITHM = "HS256"
   JWT_EXPIRY_HOURS = 24

   def create_access_token(user_id: str) -> str:
       payload = {
           "sub": user_id,
           "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
           "iat": datetime.now(timezone.utc),
       }
       return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

   def decode_access_token(token: str) -> Optional[str]:
       """Returns user_id or None if invalid/expired."""
       try:
           payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
           return payload.get("sub")
       except jwt.PyJWTError:
           return None
   ```

2. **Create `server/auth_deps.py`**
   - `get_current_user(authorization, x_api_key) -> User` — raises HTTPException(401) if no valid auth
   - `get_optional_user(authorization, x_api_key) -> Optional[User]` — returns None if no auth (for backward compat during migration)
   - Logic: check Bearer token first, then X-API-Key, then 401

3. **Create `server/auth_routes.py`**
   ```
   POST /api/auth/register  — body: RegisterIn → create user, return token
   POST /api/auth/login     — body: LoginIn → verify, return token
   GET  /api/auth/me         — requires auth → return user profile
   POST /api/auth/api-keys   — requires auth → create API key, return full key once
   GET  /api/auth/api-keys   — requires auth → list user's API keys (prefix only)
   DELETE /api/auth/api-keys/{key_id} — requires auth → revoke key
   ```

4. **Update `server/main.py`**
   - Add `from auth_routes import router as auth_router`
   - Add `app.include_router(auth_router)`
   - Update CORS: read `AGENTLENS_CORS_ORIGINS` env var, default `["*"]` for backward compat
   - Registration gate: if `AGENTLENS_DISABLE_REGISTER=true`, disable register endpoint (admin creates users)

## Response Schemas

### Login Response
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "User",
    "is_admin": false
  }
}
```

### API Key Creation Response
```json
{
  "api_key": {
    "id": "uuid",
    "key_prefix": "al_a1b2...",
    "name": "my-agent-key",
    "created_at": "2026-02-28T..."
  },
  "full_key": "al_a1b2c3d4e5f6..."  // shown once, never returned again
}
```

## Todo List
- [ ] Create auth_jwt.py with encode/decode helpers
- [ ] Create auth_deps.py with get_current_user dependency
- [ ] Create auth_routes.py with register/login/me/api-keys endpoints
- [ ] Register auth_router in main.py
- [ ] Test login flow manually

## Success Criteria
- `POST /api/auth/register` creates user, returns JWT
- `POST /api/auth/login` validates credentials, returns JWT
- `GET /api/auth/me` with valid Bearer token returns user
- `POST /api/auth/api-keys` creates prefixed key, returns full key
- 401 returned when no/invalid auth provided to protected endpoints
- `/api/health` remains publicly accessible

## Risk Assessment
- **JWT secret rotation**: If `AGENTLENS_JWT_SECRET` not set, auto-generated secret resets on restart → all tokens invalidated. Document: set env var in production.
- **Registration abuse**: Mitigate with `AGENTLENS_DISABLE_REGISTER` env var

## Security Considerations
- JWT expiry: 24 hours (configurable via env var later)
- No refresh tokens in v1 (KISS) — user re-logs after expiry
- API key validation updates `last_used_at` for audit trail
- Passwords validated via bcrypt.checkpw (constant-time)
- Never log tokens or API keys
