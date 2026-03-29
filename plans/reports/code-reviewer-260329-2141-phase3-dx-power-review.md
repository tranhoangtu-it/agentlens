---
type: code-review
date: 2026-03-29
scope: Phase 3 "DX & Power" — Replay Sandbox, Go CLI, VS Code Extension
files_reviewed: 20
---

# Code Review: Phase 3 — DX & Power

## Overall Assessment

Solid implementation across all three features. Good tenant isolation on replay sessions, proper config file permissions in CLI, clean VS Code extension lifecycle. Several issues found, most medium severity, two critical.

---

## Critical Issues

### 1. [CRITICAL] Replay routes: `modifications_json` has no size limit — stored as unbounded string
**File:** `server/replay_models.py:18`, `server/replay_routes.py:44`

`modifications_json` is a plain `str` column with no max length. An attacker can POST megabytes of modification data per session. The `modifications: dict = {}` Pydantic field also has no size validation.

**Impact:** Storage exhaustion, potential DoS.
**Fix:** Add a max-size validator on `ReplaySessionIn.modifications`:
```python
from pydantic import validator

@validator('modifications')
def validate_size(cls, v):
    import json
    if len(json.dumps(v)) > 65536:  # 64KB limit
        raise ValueError('modifications too large')
    return v
```

### 2. [CRITICAL] CLI: trace ID passed unsanitized into URL path — SSRF/path traversal
**File:** `cli/cmd/traces.go:147`, `cli/internal/api/client.go:32`

```go
resp, err := client.Get("/api/traces/"+traceID, nil)
```

`traceID` comes from user CLI args with no validation. A malicious value like `../../admin/users` gets concatenated into the URL path. The `client.Get` just does `c.BaseURL + path`, so the full URL becomes attacker-controlled path segments.

**Impact:** Possible SSRF against internal endpoints if the AgentLens server proxies or if the CLI is pointed at a gateway.
**Fix:** Validate trace IDs match expected format (UUID or similar) before building URL, or use `url.PathEscape(traceID)`:
```go
resp, err := client.Get("/api/traces/"+url.PathEscape(traceID), nil)
```
Same issue in `traces diff` (line 276-277) with `id1`/`id2`.

---

## High Priority

### 3. [WARNING] Dashboard: `deleteReplaySession` silently swallows errors
**File:** `dashboard/src/lib/replay-api-client.ts:39-41`

```ts
export async function deleteReplaySession(id: string): Promise<void> {
  await fetchWithAuth(`${BASE}/replay-sessions/${id}`, { method: 'DELETE' })
}
```

No status check on response. If delete fails (403, 404, 500), caller gets no indication. Contrast with `createReplaySession` which checks `res.ok`.

**Fix:** Add `if (!res.ok) throw new Error(...)` like the other methods.

### 4. [WARNING] Dashboard: `handleSaveSession` catch block silently ignores errors
**File:** `dashboard/src/pages/trace-replay-page.tsx:85`

```ts
} catch { /* ignore */ }
```

User clicks "Save", API returns 422 (invalid span IDs) or 500 — no feedback shown. The button just resets to default state.

**Fix:** Show error via toast or state:
```ts
} catch (e) {
  setError(e instanceof Error ? e.message : 'Failed to save session')
}
```

### 5. [WARNING] Dashboard: `replay-api-client` doesn't encode `traceId` in URL
**File:** `dashboard/src/lib/replay-api-client.ts:34`

```ts
const res = await fetchWithAuth(`${BASE}/traces/${traceId}/replay-sessions`)
```

If `traceId` contains URL-special characters (unlikely for UUIDs but possible if IDs change format), this breaks. VS Code extension correctly uses `encodeURIComponent`.

**Fix:** `${BASE}/traces/${encodeURIComponent(traceId)}/replay-sessions`

### 6. [WARNING] VS Code extension: `openTrace` command receives wrong argument type
**File:** `vscode-extension/src/extension.ts:50-56` vs `trace-tree-provider.ts:22-24`

The TreeItem's `command.arguments` passes the `trace: TraceRecord` object:
```ts
this.command = { command: "agentlens.openTrace", arguments: [trace] };
```

But the handler expects a `TraceItem`:
```ts
async (item: TraceItem | undefined) => {
  if (item.trace.id.startsWith("__")) { ... }
```

When clicked, VS Code passes the raw `TraceRecord`, not the `TraceItem` wrapper. So `item.trace` is `undefined` — accessing `.trace.id` throws. The guard `item.trace.id.startsWith("__")` will crash at runtime.

**Fix:** Either pass `[this]` as argument (the TraceItem) or handle TraceRecord directly:
```ts
async (item: TraceItem | TraceRecord | undefined) => {
  const id = 'trace' in item ? item.trace.id : item.id;
```

### 7. [WARNING] SSE parser: no `bufio.Scanner` buffer size limit
**File:** `cli/internal/stream/sse.go:51`

`bufio.NewScanner(r)` defaults to 64KB max token size. If the server sends a data line >64KB, `scanner.Scan()` silently returns false and `scanner.Err()` returns a "token too long" error, disconnecting the stream without clear user feedback.

**Fix:** Set a larger buffer or add explicit error messaging:
```go
scanner := bufio.NewScanner(r)
scanner.Buffer(make([]byte, 0, 256*1024), 256*1024) // 256KB
```

---

## Medium Priority

### 8. [INFO] Replay storage: `_get_engine()` called per function — engine not cached at module level
**File:** `server/replay_storage.py:14,31,42,51`

Every CRUD call invokes `_get_engine()`. If `_get_engine()` creates a new engine each time (depends on implementation), this creates connection pool churn. If it's already cached (likely), this is just a style issue.

### 9. [INFO] VS Code extension: `treeProvider.getTraces()` always returns array, condition is always true
**File:** `vscode-extension/src/extension.ts:33`

```ts
if (traces.length > 0 || !treeProvider.getTraces()) {
```

`getTraces()` returns `this.traces` which is initialized as `[]` — never falsy. The `||` branch never triggers. This condition should likely be `traces.length > 0` only, or removed entirely to always update status bar (including showing "0 traces").

### 10. [INFO] Replay model: `ReplaySessionIn.modifications` typed as bare `dict`
**File:** `server/replay_models.py:30`

```python
modifications: dict = {}  # {span_id: {input: "new input"}}
```

No type enforcement on dict shape. Callers could send `{"span_id": "arbitrary_string"}` instead of `{"span_id": {"input": "..."}}`. The server stores whatever is sent.

**Fix:** Use typed dict: `modifications: dict[str, dict[str, str]] = {}`

### 11. [INFO] CLI `config show` prints API key to stdout (masked but partial)
**File:** `cli/cmd/config.go:74-76`

Shows first 4 and last 4 characters. For short API keys (9-12 chars), this reveals most of the key. Current guard only fully masks keys <= 8 chars.

**Fix:** Mask more aggressively — show only last 4 characters regardless of length.

### 12. [INFO] VS Code extension: auto-refresh runs even when server is unreachable
**File:** `vscode-extension/src/trace-tree-provider.ts:140-143`

The 30s `setInterval` fires unconditionally. If the server is down, every tick produces a failed HTTP request and error state. No exponential backoff.

**Fix:** After N consecutive failures, increase interval or pause auto-refresh until manual refresh succeeds.

### 13. [INFO] Dashboard: `replay-sandbox-panel` computes `span.end_ms - span.start_ms` without null check
**File:** `dashboard/src/components/replay-sandbox-panel.tsx:54`

Dashboard `Span.end_ms` is typed as `number` (non-nullable), but VS Code extension `SpanRecord.end_ms` is `number | null`. If the types diverge or a running span comes in, this could show `NaN`.

### 14. [INFO] Go CLI: `push` command reads entire stdin into memory
**File:** `cli/cmd/push.go:39`

```go
data, err := io.ReadAll(os.Stdin)
```

No size limit. Piping a large file exhausts CLI memory. Add `io.LimitReader`:
```go
data, err := io.ReadAll(io.LimitReader(os.Stdin, 10*1024*1024)) // 10MB
```

---

## Positive Observations

- **Tenant isolation** on replay sessions is correctly implemented — every read/write checks `user_id` ownership
- **CLI config file permissions** use `0700` for dir and `0600` for file — proper secret protection
- **VS Code extension lifecycle** is clean — all disposables registered, timer cleared on deactivate
- **SSE parser** handles multi-line `data:` fields and comment lines correctly per SSE spec
- **WebView panel** properly escapes all HTML output via `esc()` function — no XSS
- **Config change reactivity** in VS Code extension rebuilds client and refreshes tree — good UX
- **CLI error messages** are user-friendly with actionable hints ("run: agentlens config set endpoint...")
- **Replay controls hook** uses refs to avoid stale closure bugs in setInterval — correct pattern

---

## Unresolved Questions

1. Does `storage._get_engine()` cache the engine? If not, replay_storage creates a new engine per call.
2. Is there an Alembic migration for the `replay_session` table? SQLModel `table=True` won't auto-create it without one.
3. The VS Code extension stores API key in VS Code settings (plaintext in `settings.json`) — is there a plan to use `SecretStorage` API instead?
