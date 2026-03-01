# Phase 1: 100% Test Coverage

## Context Links
- Server tests: `server/tests/` (7 test files, ~1446 lines, 86 tests)
- TS SDK tests: `sdk-ts/tests/` (3 test files, 30 tests)
- Run server: `cd server && pytest tests/ --cov --cov-report=term-missing`
- Run TS SDK: `cd sdk-ts && npm test`

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 5h
- Raise coverage from 86% to 100% across server + TS SDK

## Key Insights
- **diff.py (19% covered)**: 218 lines, zero dedicated tests. `compute_diff` exercised only via `/api/traces/compare` endpoint. `build_span_tree`, `_flatten_tree`, `match_spans` untested directly.
- **auth_seed.py (40% covered)**: 56 lines. `seed_admin()` runs in `lifespan()` but tests never exercise it directly. `_migrate_orphan_data` uncovered.
- **alert_notifier.py (56% covered)**: 49 lines. `publish_alert_sse` partially tested via alert endpoint tests. `fire_webhook` uses `urllib.request` in background thread — never tested.
- **alert_evaluator.py**: Indirectly tested via trace ingestion that triggers evaluation. Direct unit tests for `_compute_metric`, `_get_baseline_avg`, `_build_message`, cooldown logic needed.
- **auth_deps.py**: `get_optional_user` function never tested.
- **sse.py**: `QueueFull` dead subscriber cleanup untested.

## Requirements

### Functional
- Every Python source file must reach 100% line coverage
- Every TS SDK source file must reach 100% line coverage
- Tests must be real (no mocks that bypass logic, no `# pragma: no cover`)

### Non-functional
- Tests run in <30s total (server)
- No flaky tests (no sleep-based timing)

## Related Code Files

### Files to CREATE
- `server/tests/test_diff.py` — dedicated diff algorithm tests
- `server/tests/test_auth_seed.py` — seed_admin + orphan migration tests
- `server/tests/test_alert_notifier.py` — SSE publish + webhook tests
- `server/tests/test_alert_evaluator.py` — unit tests for metric computation, baseline, message building

### Files to MODIFY
- `server/tests/test_auth.py` — add `get_optional_user` test, X-API-Key header test
- `server/tests/test_sse.py` — add QueueFull cleanup test

## Implementation Steps

### 1. test_diff.py (~15 tests)

```python
# Test build_span_tree
- test_build_tree_single_root: 1 span, no parent → [SpanNode(depth=0)]
- test_build_tree_nested: parent→child→grandchild, verify depths 0/1/2
- test_build_tree_orphan_parent: span with parent_id not in list → treated as root
- test_build_tree_sibling_index: 3 children of same parent → sibling_index 0,1,2

# Test _flatten_tree
- test_flatten_preserves_dfs_order: nested tree → flat list in DFS order

# Test match_spans
- test_match_identical_trees: same structure → all matched, no left/right only
- test_match_left_only: extra span in left → appears in left_only
- test_match_right_only: extra span in right → appears in right_only
- test_match_by_key_tuple: spans matched by (name, type, depth, sibling_index)

# Test compute_diff
- test_diff_identical_spans: same input/output → status "identical"
- test_diff_changed_spans: different input/output → status "changed"
- test_diff_duration_delta: different start/end → duration_delta_ms computed
- test_diff_cost_delta: different cost_usd → cost_delta_usd computed
- test_diff_token_delta: different token counts → deltas computed
- test_diff_null_times: None start/end → deltas are None
- test_diff_empty_spans: empty lists → empty result
```

### 2. test_auth_seed.py (~5 tests)

```python
- test_seed_admin_creates_user: fresh DB → admin user created with expected email
- test_seed_admin_idempotent: call twice → only one admin user
- test_seed_admin_custom_env: set AGENTLENS_ADMIN_EMAIL/PASSWORD env vars → uses those
- test_migrate_orphan_traces: insert trace with user_id=NULL, run seed → user_id set to admin
- test_migrate_orphan_alert_rules: insert alert_rule with user_id=NULL → migrated
```

Key: use `monkeypatch.setenv` for env vars, directly call `seed_admin()` after DB setup.

### 3. test_alert_notifier.py (~4 tests)

```python
- test_publish_alert_sse: mock bus.publish, verify event_type and data shape
- test_fire_webhook_success: start HTTP server (http.server), call fire_webhook, verify POST received
- test_fire_webhook_failure: call with invalid URL → no exception raised (logged)
- test_fire_webhook_timeout: slow server → times out without crash
```

For webhook tests: use `unittest.mock.patch("urllib.request.urlopen")` or a real `http.server.HTTPServer` on localhost.

### 4. test_alert_evaluator.py (~10 tests)

```python
# _compute_metric
- test_compute_metric_cost: trace.total_cost_usd=0.5 → returns 0.5
- test_compute_metric_latency: trace.duration_ms=1000 → returns 1000.0
- test_compute_metric_error_rate: 2 spans, 1 missing end_ms → returns 0.5
- test_compute_metric_error_rate_no_spans: empty spans → returns None
- test_compute_metric_missing_span: always returns None (handled separately)
- test_compute_metric_unknown: unknown metric → returns None

# _get_baseline_avg
- test_baseline_avg_cost: 3 past traces with costs → average
- test_baseline_avg_no_traces: no past traces → None
- test_baseline_avg_excludes_current: current trace excluded from baseline

# _build_message
- test_build_message_format: verify "Cost = 0.5 gt 0.1 (rule: my-rule)" format

# _evaluate_single_rule (integration-level)
- test_cooldown_skips: last event <60s ago → returns None
- test_relative_mode: threshold * baseline comparison
```

### 5. Additions to test_auth.py (~3 tests)

```python
- test_get_optional_user_no_auth: request without auth → returns None (not 401)
- test_auth_via_x_api_key_header: X-API-Key header works for ingestion
- test_auth_invalid_bearer_token: expired/invalid JWT → 401
```

### 6. Additions to test_sse.py (~2 tests)

```python
- test_queue_full_cleanup: fill subscriber queue to maxsize → publish drops subscriber
- test_user_filtering: subscriber with user_id only receives matching events
```

### 7. TS SDK coverage gaps (sdk-ts)

Review `sdk-ts/tests/` for uncovered branches:
- `cost.ts`: edge cases (unknown model, zero tokens)
- `tracer.ts`: nested trace error handling, currentTrace when no active trace
- `transport.ts`: batch flush edge cases, network error handling

## Todo List

- [ ] Create `test_diff.py` with ~15 tests
- [ ] Create `test_auth_seed.py` with ~5 tests
- [ ] Create `test_alert_notifier.py` with ~4 tests
- [ ] Create `test_alert_evaluator.py` with ~10 tests
- [ ] Add 3 tests to `test_auth.py`
- [ ] Add 2 tests to `test_sse.py`
- [ ] Run `pytest --cov --cov-report=term-missing` → verify 100%
- [ ] Review TS SDK coverage, add missing tests
- [ ] Run `cd sdk-ts && npm test` → verify all pass
- [ ] Final combined run: all 100%+ tests passing

## Success Criteria
- `pytest --cov` shows 100% (or 99%+ with only unreachable lines)
- `vitest run` — all TS SDK tests pass
- No mocks that bypass real logic
- All tests run in <30s

## Risk Assessment
- **auth_seed.py** tests need careful DB state setup — seed_admin imports from auth_storage which uses global engine
- **alert_evaluator** tests need traces + rules + events in DB — use existing fixture patterns
- **fire_webhook** background thread timing — use mock or threading.Event for synchronization

## Security Considerations
- Tests must not hardcode real credentials
- Webhook tests must use localhost only
