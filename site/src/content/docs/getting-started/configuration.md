---
title: Configuration
description: Environment variables and configuration options for AgentLens
---

AgentLens is configured via environment variables. All variables are optional — sensible defaults are provided for local development.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTLENS_JWT_SECRET` | auto-generated | JWT signing secret. **Set this in production.** |
| `AGENTLENS_ADMIN_EMAIL` | `admin@agentlens.local` | Default admin account email |
| `AGENTLENS_ADMIN_PASSWORD` | `changeme` | Default admin account password. **Change in production.** |
| `AGENTLENS_CORS_ORIGINS` | `localhost:3000,localhost:5173` | Comma-separated list of allowed CORS origins |
| `DATABASE_URL` | `sqlite:///./agentlens.db` | Database connection string |

## Database Options

### SQLite (Default)

```bash
# Relative path (default)
DATABASE_URL=sqlite:///./agentlens.db

# Absolute path
DATABASE_URL=sqlite:////data/agentlens.db
```

SQLite uses WAL mode by default for better concurrent read performance.

### PostgreSQL

```bash
DATABASE_URL=postgresql://user:password@host:5432/agentlens
```

PostgreSQL is recommended for production deployments with multiple users or high trace volume.

## Production Checklist

```bash
# Generate a strong JWT secret
openssl rand -hex 32

# Set all required vars
export AGENTLENS_JWT_SECRET=<generated-above>
export AGENTLENS_ADMIN_EMAIL=admin@yourcompany.com
export AGENTLENS_ADMIN_PASSWORD=<strong-password>
export DATABASE_URL=postgresql://user:pass@host:5432/agentlens
```

## SDK Configuration

### Python

```python
import agentlens

agentlens.configure(
    server_url="http://localhost:3000",
    api_key="al_your_api_key",     # from Settings → API Keys in dashboard
    batch_size=50,                  # flush every 50 spans (default: 1)
    batch_interval=5.0,             # or every 5 seconds
)
```

### TypeScript

```typescript
import * as agentlens from "agentlens-observe";

agentlens.configure({
  serverUrl: "http://localhost:3000",
  apiKey: "al_your_api_key",
  batchSize: 50,
  batchInterval: 5000,  // milliseconds
});
```

## API Key Authentication

Generate API keys from the dashboard under **Settings → API Keys**, then use them in SDK configuration or direct API calls:

```bash
curl -H "X-API-Key: al_your_api_key" http://localhost:3000/api/traces
```
