---
title: Authentication
description: Multi-tenant auth with JWT sessions and API key support
---

AgentLens includes a full multi-tenant authentication system — each user's traces, alert rules, and API keys are fully isolated.

## Default Admin Account

On first startup, AgentLens creates a default admin account:

| Field | Default |
|-------|---------|
| Email | `admin@agentlens.local` |
| Password | `changeme` |

**Change the password immediately in production.**

## Login

Navigate to [http://localhost:3000](http://localhost:3000) — you'll be redirected to the login page automatically.

Enter your email and password to receive a JWT session (valid for 24 hours).

## User Registration

New users can register at `/register` on the dashboard. Each user's data is fully isolated — they cannot access other users' traces or alert rules.

## API Keys

For programmatic access (SDKs, CI/CD), use API keys instead of JWT sessions.

### Creating an API Key

1. Log in to the dashboard
2. Navigate to **Settings → API Keys**
3. Click **Generate New Key**
4. Copy the key — it is shown only once

Keys use the `al_` prefix (e.g., `al_abc123...`). They are stored as SHA-256 hashes — AgentLens cannot recover a lost key.

### Using an API Key

**SDK configuration:**

```python
agentlens.configure(
    server_url="http://localhost:3000",
    api_key="al_your_key_here",
)
```

```typescript
agentlens.configure({
  serverUrl: "http://localhost:3000",
  apiKey: "al_your_key_here",
});
```

**Direct API calls:**

```bash
curl -H "X-API-Key: al_your_key_here" http://localhost:3000/api/traces
```

## JWT Configuration

```bash
# Set a strong secret for production
export AGENTLENS_JWT_SECRET=$(openssl rand -hex 32)
```

JWTs are HS256-signed, expire after 24 hours, and include the user's ID and email as claims.

## Security Notes

- Passwords are hashed with bcrypt (cost factor 12)
- API keys are SHA-256 hashed before storage
- All data endpoints enforce per-user isolation — cross-tenant access returns 404
- SSE streams filter events by user ID — users only receive their own trace events
