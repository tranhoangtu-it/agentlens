# Phase 3 — Tenant Isolation

## Context Links
- [storage.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/storage.py) — all trace CRUD functions
- [alert_storage.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/alert_storage.py) — alert CRUD functions
- [alert_evaluator.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/alert_evaluator.py) — alert rule evaluation
- [main.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/main.py) — route handlers pass through to storage
- [Phase 2](phase-02-auth-middleware.md) — `get_current_user` dependency

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: Add `user_id` column to Trace and AlertRule tables. Filter all queries by the authenticated user's ID so each user sees only their own data.

## Key Insights
- Current storage functions take no user context — must add `user_id` parameter
- Main routes call storage directly — must inject `current_user` from dependency and pass `user_id`
- AlertRule and AlertEvent should also be tenant-scoped
- Span table does NOT need `user_id` — spans belong to a trace; filter trace first, spans follow
- SSE stream currently broadcasts to all subscribers — must filter by user_id

## Architecture

### Database Changes

**Trace table** — add column:
```python
user_id: Optional[str] = Field(default=None, index=True)
```

**AlertRule table** — add column:
```python
user_id: Optional[str] = Field(default=None, index=True)
```

**AlertEvent table** — add column:
```python
user_id: Optional[str] = Field(default=None, index=True)
```

`Optional[str]` with `default=None` ensures backward compat with existing rows (migrated to "default" tenant in Phase 5).

### Query Filter Pattern

Every storage function that reads/writes tenant data adds:
```python
if user_id:
    stmt = stmt.where(Trace.user_id == user_id)
```

### SSE Tenant Filtering

Current SSE bus broadcasts to all subscribers. Options:
1. **Per-user queues** — SSEBus tracks user_id per subscriber, only sends events for that user
2. **Client-side filter** — send all events, client ignores irrelevant ones

Choice: **Per-user queues** (server-side filtering). Prevents data leakage. Modify `bus.publish()` to accept `user_id`, and `bus.subscribe()` to accept `user_id` filter.

## Related Code Files

### Files to Modify
1. `server/models.py` — add `user_id` column to `Trace`
2. `server/alert_models.py` — add `user_id` column to `AlertRule` and `AlertEvent`
3. `server/storage.py` — add `user_id` param to `create_trace`, `list_traces`, `get_trace`, `get_trace_pair`, `add_spans_to_trace`, `list_agents`
4. `server/alert_storage.py` — add `user_id` param to all CRUD functions
5. `server/alert_evaluator.py` — pass `user_id` through evaluation chain
6. `server/main.py` — inject `current_user` into all data routes, pass `user_id` to storage
7. `server/sse.py` — add user_id filtering to SSEBus

## Implementation Steps

1. **Add `user_id` column to models**
   - `models.py` — `Trace`: add `user_id: Optional[str] = Field(default=None, index=True)`
   - `alert_models.py` — `AlertRule`: add `user_id: Optional[str] = Field(default=None, index=True)`
   - `alert_models.py` — `AlertEvent`: add `user_id: Optional[str] = Field(default=None, index=True)`

2. **Update `storage.py` functions**
   - `create_trace(trace_id, agent_name, spans_data, user_id=None)` — set `trace.user_id = user_id`
   - `list_traces(..., user_id=None)` — add `.where(Trace.user_id == user_id)` when user_id provided
   - `get_trace(trace_id, user_id=None)` — add user_id check to prevent cross-tenant read
   - `get_trace_pair(left_id, right_id, user_id=None)` — check both traces belong to user
   - `add_spans_to_trace(trace_id, spans_data, user_id=None)` — verify trace ownership before adding spans
   - `list_agents(user_id=None)` — filter by user_id

3. **Update `alert_storage.py` functions**
   - `create_alert_rule(data)` — data dict includes `user_id`
   - `list_alert_rules(..., user_id=None)` — filter by user_id
   - `list_alert_events(..., user_id=None)` — filter by user_id
   - `get_unresolved_alert_count(user_id=None)` — filter by user_id

4. **Update `alert_evaluator.py`**
   - `evaluate_alert_rules(trace_id, agent_name)` — read `user_id` from trace, pass to alert event creation
   - Rule lookup: filter rules by `user_id` of the trace owner

5. **Update `main.py` route handlers**
   - Import `get_current_user` from `auth_deps`
   - Add `current_user: User = Depends(get_current_user)` to:
     - `ingest_trace` — pass `current_user.id` to `create_trace`
     - `ingest_spans` — verify trace belongs to user before appending
     - `list_traces_endpoint` — pass `current_user.id` to `list_traces`
     - `list_agents_endpoint` — pass `current_user.id`
     - `get_trace_endpoint` — pass `current_user.id` for ownership check
     - `compare_traces_endpoint` — pass `current_user.id`
     - `stream_traces` — pass `current_user.id` to SSE subscribe
   - Alert routes: add `current_user` dependency, pass `user_id`
   - OTel endpoint: use API key auth → `current_user.id`

6. **Update `sse.py` SSEBus**
   ```python
   def publish(self, event_type, data, user_id=None):
       # Only send to subscribers matching user_id (or all if user_id is None)

   async def subscribe(self, user_id=None):
       # Store user_id with queue, filter in publish
   ```

## Todo List
- [ ] Add user_id column to Trace model
- [ ] Add user_id column to AlertRule and AlertEvent models
- [ ] Update all storage.py functions with user_id parameter
- [ ] Update all alert_storage.py functions with user_id parameter
- [ ] Update alert_evaluator.py to propagate user_id
- [ ] Update main.py routes to inject current_user and pass user_id
- [ ] Update alert_routes.py to inject current_user
- [ ] Update SSEBus with per-user filtering
- [ ] Verify cross-tenant access returns 404 (not 403 — don't leak existence)

## Success Criteria
- User A cannot see User B's traces, alerts, or alert rules
- `GET /api/traces` returns only current user's traces
- `GET /api/traces/{id}` returns 404 for other user's trace
- SDK with User A's API key creates traces owned by User A
- SSE stream only delivers events for the subscribed user
- Existing data (user_id=NULL) remains accessible to admin during migration

## Risk Assessment
- **Breaking change**: All routes now require auth → existing SDK without API key will fail. Mitigate: Phase 5 provides migration path, env var `AGENTLENS_AUTH_REQUIRED=false` disables auth temporarily.
- **SSE complexity**: Per-user filtering adds state to SSEBus. Keep simple — dict of `{user_id: [queues]}`.
- **Performance**: Adding `.where(user_id=...)` to every query. user_id is indexed, negligible impact.

## Security Considerations
- Cross-tenant reads return 404 (not 403) to prevent enumeration
- Span data inherits tenant from parent trace — no separate user_id on Span table
- Admin users can optionally see all data (add `is_admin` bypass later if needed)
