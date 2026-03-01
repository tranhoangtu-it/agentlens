---
title: REST API
description: Complete REST API reference for AgentLens server
---

All endpoints are prefixed with the server base URL (e.g., `http://localhost:3000`).

Authentication: pass `Authorization: Bearer <jwt>` or `X-API-Key: al_<key>` on all protected endpoints.

## Authentication

### `POST /api/auth/register`

Create a new user account.

```json
// Request
{ "email": "user@example.com", "password": "strongpassword" }

// Response 201
{ "id": "user_abc", "email": "user@example.com" }
```

### `POST /api/auth/login`

Exchange credentials for a JWT.

```json
// Request
{ "email": "user@example.com", "password": "strongpassword" }

// Response 200
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### `GET /api/auth/me`

Return current authenticated user info.

```json
// Response 200
{ "id": "user_abc", "email": "user@example.com", "created_at": "2026-03-01T00:00:00Z" }
```

### `POST /api/auth/api-keys`

Generate a new API key for the authenticated user.

```json
// Response 201
{ "key": "al_abc123...", "id": "key_xyz", "created_at": "2026-03-01T00:00:00Z" }
```

### `GET /api/auth/api-keys`

List all API keys for the authenticated user (keys are masked).

### `DELETE /api/auth/api-keys/{id}`

Revoke an API key.

---

## Traces

### `POST /api/traces`

Create a new trace.

```json
// Request
{
  "id": "trace_abc",
  "agent_name": "ResearchAgent",
  "status": "running",
  "metadata": {}
}

// Response 201
{ "id": "trace_abc", "agent_name": "ResearchAgent", ... }
```

### `GET /api/traces`

List traces with optional filters.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Full-text search on agent_name and span names |
| `status` | string | `running`, `success`, `error` |
| `agent` | string | Filter by agent_name |
| `from` | ISO date | Start date filter |
| `to` | ISO date | End date filter |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Results per page (default: 20, max: 100) |
| `sort` | string | `created_at`, `duration`, `cost` |
| `order` | string | `asc`, `desc` |

### `GET /api/traces/{id}`

Fetch a single trace with all spans.

### `PATCH /api/traces/{id}`

Update trace status or metadata.

### `POST /api/traces/{id}/spans`

Add a span to an existing trace.

```json
// Request
{
  "id": "span_001",
  "name": "web_search",
  "kind": "tool_call",
  "status": "success",
  "input": { "query": "..." },
  "output": { "results": [...] },
  "cost_usd": 0.002,
  "duration_ms": 340
}
```

### `GET /api/traces/compare`

Compare two traces.

**Query params:** `a=<trace_id>&b=<trace_id>`

### `GET /api/traces/stream`

Server-Sent Events stream for real-time span updates.

```
// Event types
data: {"type": "span_created", "trace_id": "...", "span": {...}}
data: {"type": "trace_updated", "trace": {...}}
data: {"type": "alert_fired", "alert": {...}}
```

---

## OpenTelemetry

### `POST /api/otel/v1/traces`

Receive OTLP HTTP JSON spans. Accepts standard `ExportTraceServiceRequest` payload.

---

## Alert Rules

### `POST /api/alert-rules`

Create a new alert rule.

```json
{
  "name": "High cost",
  "type": "cost_spike",
  "threshold": 0.10,
  "mode": "absolute",
  "baseline_window": 10,
  "cooldown_seconds": 60,
  "webhook_url": "https://hooks.slack.com/..."
}
```

### `GET /api/alert-rules`

List all alert rules for the authenticated user.

### `PUT /api/alert-rules/{id}`

Update an alert rule.

### `DELETE /api/alert-rules/{id}`

Delete an alert rule.

---

## Alert Events

### `GET /api/alerts`

List fired alert events.

**Query params:** `resolved=true|false`, `page`, `page_size`

### `PATCH /api/alerts/{id}`

Mark an alert event as resolved.

```json
{ "resolved": true }
```
