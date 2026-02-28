# Phase 6: Testing Suite

## Context Links
- Server source: `server/` (main.py, models.py, sse.py, storage.py — 314 LOC)
- SDK source: `sdk/agentlens/` (467 LOC)
- Dashboard source: `dashboard/src/` (732 LOC)
- No existing tests anywhere in the codebase

## Overview
- **Priority**: P2
- **Status**: pending
- **Effort**: 4h
- **Depends on**: All feature phases (1-5) — tests verify final code
- **Description**: Add comprehensive unit + integration tests for server and SDK. Add basic component tests for dashboard.

## Key Insights
- Zero tests currently — need to build from scratch
- Server is simple CRUD + SSE; tests focus on storage layer + API endpoints
- SDK tests focus on tracer lifecycle, span nesting, transport mocking
- Dashboard tests: component rendering + API mocking (Vitest + React Testing Library)
- Target 80%+ coverage on server + SDK; 60%+ on dashboard

## Requirements

### Functional
- **Server tests**: Storage CRUD, API endpoints, SSE streaming, diff algorithm
- **SDK tests**: Tracer decorator (sync/async), span context manager, nesting, transport
- **Dashboard tests**: Component rendering, API mocking, filter state management

### Non-Functional
- Tests run in <30s total
- No external dependencies (mock HTTP, use in-memory SQLite)
- CI-friendly (can run in GitHub Actions)

## Architecture

### Test Structure
```
server/
  tests/
    conftest.py              # Fixtures: test DB, test client
    test_storage.py          # CRUD operations
    test_api_endpoints.py    # FastAPI TestClient
    test_sse.py              # SSE bus publish/subscribe
    test_diff.py             # Trace diff algorithm (Phase 4)

sdk/
  tests/
    conftest.py              # Fixtures: mock transport
    test_tracer.py           # Decorator + context manager
    test_transport.py        # HTTP transport
    test_cost.py             # Cost calculation
    test_integrations.py     # Integration stubs

dashboard/
  src/__tests__/
    trace-list-table.test.tsx
    trace-topology-graph.test.tsx
    api-client.test.ts
    use-trace-filters.test.ts
```

### Test Dependencies
```
# Server
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27  # Already a dependency, used for TestClient

# SDK
pytest>=8.0
respx>=0.21  # Mock httpx requests

# Dashboard
vitest + @testing-library/react (add to devDependencies)
```

## Related Code Files

### Files to Modify
- `server/requirements.txt` — add test dependencies section
- `sdk/pyproject.toml` — add `[project.optional-dependencies] dev = [...]`
- `dashboard/package.json` — add vitest + testing-library

### Files to Create
- `server/tests/conftest.py`
- `server/tests/test_storage.py`
- `server/tests/test_api_endpoints.py`
- `server/tests/test_sse.py`
- `server/tests/test_diff.py`
- `server/pytest.ini` (or section in pyproject.toml)
- `sdk/tests/conftest.py`
- `sdk/tests/test_tracer.py`
- `sdk/tests/test_transport.py`
- `sdk/tests/test_cost.py`
- `dashboard/vitest.config.ts`
- `dashboard/src/__tests__/trace-list-table.test.tsx`
- `dashboard/src/__tests__/api-client.test.ts`

## Implementation Steps

### Step 1: Server test infrastructure
1. Create `server/tests/conftest.py`:
   ```python
   import pytest
   from fastapi.testclient import TestClient
   from sqlmodel import SQLModel, create_engine, Session
   from main import app
   import storage

   @pytest.fixture(autouse=True)
   def test_db(tmp_path):
       """Use fresh in-memory SQLite for each test."""
       db_path = tmp_path / "test.db"
       engine = create_engine(f"sqlite:///{db_path}")
       SQLModel.metadata.create_all(engine)
       storage._engine = engine
       yield engine

   @pytest.fixture
   def client():
       return TestClient(app)
   ```

### Step 2: Server storage tests
1. Create `server/tests/test_storage.py`:
   - `test_create_trace_basic` — create trace with spans, verify aggregates
   - `test_create_trace_upsert` — create same trace_id twice, verify update
   - `test_list_traces_pagination` — create 20 traces, verify offset/limit
   - `test_list_traces_filter_agent_name` — filter by agent_name
   - `test_list_traces_filter_status` — filter by status (Phase 2)
   - `test_list_traces_filter_date_range` — filter by date (Phase 2)
   - `test_get_trace_not_found` — returns None for missing ID
   - `test_get_trace_with_spans` — returns trace + all spans

### Step 3: Server API endpoint tests
1. Create `server/tests/test_api_endpoints.py`:
   - `test_health` — GET /api/health returns 200
   - `test_ingest_trace` — POST /api/traces returns 201
   - `test_ingest_trace_invalid` — invalid body returns 422
   - `test_list_traces` — GET /api/traces returns traces
   - `test_get_trace` — GET /api/traces/{id} returns detail
   - `test_get_trace_404` — missing trace returns 404
   - `test_compare_traces` — GET /api/traces/compare (Phase 4)

### Step 4: Server SSE tests
1. Create `server/tests/test_sse.py`:
   - `test_publish_subscribe` — publish event, verify subscriber receives it
   - `test_multiple_subscribers` — all subscribers get same event
   - `test_queue_overflow` — dead queues get cleaned up

### Step 5: SDK test infrastructure
1. Create `sdk/tests/conftest.py`:
   ```python
   import pytest
   import respx

   @pytest.fixture(autouse=True)
   def mock_transport():
       """Mock all HTTP calls from SDK transport."""
       with respx.mock:
           respx.post("http://localhost:3000/api/traces").respond(201)
           yield
   ```

### Step 6: SDK tracer tests
1. Create `sdk/tests/test_tracer.py`:
   - `test_trace_decorator_sync` — basic sync function tracing
   - `test_trace_decorator_async` — async function tracing
   - `test_trace_captures_input_output` — verify span data
   - `test_nested_spans` — parent_id chain is correct
   - `test_span_outside_trace_is_noop` — no crash, no data
   - `test_trace_with_exception` — error metadata captured, exception re-raised
   - `test_cost_set_on_span` — verify cost calculation

### Step 7: SDK transport tests
1. Create `sdk/tests/test_transport.py`:
   - `test_post_trace_fires_thread` — verify non-blocking
   - `test_post_trace_handles_error` — server down doesn't crash
   - `test_custom_server_url` — AGENTLENS_URL env var respected

### Step 8: SDK cost tests
1. Create `sdk/tests/test_cost.py`:
   - `test_known_model_cost` — exact pricing for gpt-4o
   - `test_unknown_model_returns_none`
   - `test_prefix_match` — "openai/gpt-4o" matches "gpt-4o"
   - `test_zero_tokens` — 0 tokens = $0

### Step 9: Dashboard test infrastructure
1. Add to `dashboard/package.json`:
   ```json
   "devDependencies": {
     "vitest": "^3.0.0",
     "@testing-library/react": "^16.0.0",
     "@testing-library/jest-dom": "^6.0.0",
     "jsdom": "^25.0.0"
   }
   ```
2. Create `dashboard/vitest.config.ts`:
   ```ts
   import { defineConfig } from 'vitest/config'
   export default defineConfig({
     test: { environment: 'jsdom', globals: true }
   })
   ```

### Step 10: Dashboard component tests
1. Create basic rendering tests:
   - `trace-list-table.test.tsx` — renders traces, empty state, click handler
   - `api-client.test.ts` — fetch mocking, error handling

## Todo List
- [ ] Set up server test infrastructure (conftest, pytest config)
- [ ] Write server storage tests (8+ test cases)
- [ ] Write server API endpoint tests (7+ test cases)
- [ ] Write server SSE tests (3+ test cases)
- [ ] Set up SDK test infrastructure (conftest with respx)
- [ ] Write SDK tracer tests (7+ test cases)
- [ ] Write SDK transport tests (3+ test cases)
- [ ] Write SDK cost tests (4+ test cases)
- [ ] Set up dashboard test infrastructure (vitest, testing-library)
- [ ] Write dashboard component tests (3+ test files)
- [ ] Verify 80%+ coverage on server + SDK
- [ ] All tests pass: `pytest` (server), `pytest` (SDK), `npm test` (dashboard)

## Success Criteria
- `cd server && pytest` — all green, >80% coverage
- `cd sdk && pytest` — all green, >80% coverage
- `cd dashboard && npm test` — all green
- Total test runtime <30s
- No flaky tests (run 3x to verify)

## Risk Assessment
- **Risk**: Async SSE tests are flaky — **Mitigation**: Use synchronous test patterns, mock asyncio.Queue
- **Risk**: React Flow component hard to test — **Mitigation**: Test data transformation (layout), not React Flow rendering

## Security Considerations
- Test fixtures use random data, no real credentials
- In-memory databases cleaned up after each test
