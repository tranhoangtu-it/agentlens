# Code Review: AgentLens Full Codebase Security & Production-Readiness

**Date:** 2026-03-30
**Scope:** Dashboard (48 files), CLI (8 files), VS Code Extension (6 files), SDK-TS (6 files), SDK-.NET (12 files)
**Mode:** Adversarial / Red-team analysis

---

## Overall Assessment

The codebase is well-structured with consistent patterns, good separation of concerns, and defensive coding practices (NoopSpanContext, fire-and-forget transport, proper HTML escaping in WebView). However, several security issues exist around authentication bypass, credential storage, and missing input validation that would matter in production.

---

## CRITICAL Issues

### C1. Auth bypass on `fetchAgents` and `fetchAlertsSummary` - uses `fetch` instead of `fetchWithAuth`
**File:** `dashboard/src/lib/api-client.ts:81`, `dashboard/src/lib/alert-api-client.ts:120`
**Impact:** These endpoints are called without authentication tokens, bypassing the auth layer entirely. If the server enforces auth on these endpoints, they will silently fail (caught and ignored). If the server does NOT enforce auth, any unauthenticated visitor can enumerate agent names and view alert counts.

```ts
// api-client.ts:81 — uses bare fetch()
export async function fetchAgents(): Promise<AgentsResponse> {
  const res = await fetch(`${BASE}/agents`)
```

```ts
// alert-api-client.ts:120 — uses bare fetch()
export async function fetchAlertsSummary(): Promise<{ unresolved_count: number }> {
  const res = await fetch(`${BASE}/alerts/summary`)
```

**Fix:** Replace `fetch()` with `fetchWithAuth()` in both locations.

### C2. SSE endpoint has no authentication
**File:** `dashboard/src/lib/use-sse-traces.ts:50`
**Impact:** The EventSource connection to `/api/traces/stream` sends no auth header. EventSource API does not support custom headers, so any user (including unauthenticated) can stream all trace data. This is a **data leak** of potentially sensitive agent execution data.

```ts
const es = new EventSource(SSE_URL)  // No auth token
```

**Fix:** Either (a) use `fetch` with ReadableStream instead of EventSource to attach Bearer header, (b) pass token as query param `?token=...` (less secure but common SSE pattern), or (c) accept this as a design decision for the SSE endpoint and document it. Option (a) is preferred.

### C3. CLI stores API key in plaintext config file
**File:** `cli/cmd/root.go:17-19`, `cli/cmd/root.go:88`
**Impact:** The API key is written to `~/.agentlens/config.json` with file permissions 0600 (good), but in plaintext JSON. On shared systems or compromised user accounts, the API key is trivially extractable.

**Mitigation (not blocking):** Good that config dir uses 0700 and file uses 0600. Document this risk. Consider supporting OS keychain integration as a future enhancement.

### C4. VS Code Extension stores API key in plaintext settings.json
**File:** `vscode-extension/src/config.ts:18`
**Impact:** The API key is read from VS Code workspace settings (`agentlens.apiKey`). VS Code settings.json is plaintext, often committed to version control. Users may accidentally leak their API key.

```ts
const apiKey = cfg.get<string>("apiKey") ?? "";
```

**Fix:** Use VS Code `SecretStorage` API (`context.secrets.store/get`) instead of workspace settings for credentials. This uses the OS keychain.

---

## HIGH Priority

### H1. Trace detail route does not URL-encode trace ID from hash
**File:** `dashboard/src/App.tsx:51-53`
**Impact:** When parsing `#/traces/<id>`, the trace ID is extracted raw from the URL. The `detail` route uses `route.id` directly without `decodeURIComponent`, while `navigateToDetail` uses `encodeURIComponent`. If a trace ID contains special characters (e.g., URL-encoded slashes), the round-trip breaks.

```ts
const detailMatch = path.match(/^traces\/(.+)$/)
if (detailMatch) return { name: 'detail', id: detailMatch[1] }
// Note: route.id is NOT decoded, but navigateToDetail encodes it
```

The `replay` route at line 50 correctly decodes: `decodeURIComponent(replayMatch[1])`, but the `detail` route at line 52 does not.

**Fix:** Add `decodeURIComponent` to the detail match: `{ name: 'detail', id: decodeURIComponent(detailMatch[1]) }`

### H2. SSE reconnect has no backoff limit
**File:** `dashboard/src/lib/use-sse-traces.ts:87-92`
**Impact:** On persistent SSE failures (e.g., server down), the client reconnects every 3 seconds indefinitely, creating ongoing load against a potentially recovering server and filling browser network logs.

**Fix:** Add exponential backoff with a cap (e.g., max 60s delay), and optionally a max retry count.

### H3. Unbounded `io.ReadAll` on CLI HTTP responses
**File:** `cli/cmd/traces.go:78`, `cli/cmd/push.go:62`, `cli/internal/api/client.go:122`
**Impact:** CLI reads full HTTP response body into memory with no size limit. A malicious or misconfigured server could return a multi-GB response, causing OOM.

The `checkStatus` function at `client.go:122` uses `LimitReader(resp.Body, 512)` for errors (good), but success paths in `traces.go` and `push.go` use unrestricted `io.ReadAll`.

**Fix:** Use `io.LimitReader` with a reasonable cap (e.g., 10MB) on all `io.ReadAll` calls.

### H4. SSE parser has unbounded buffer in Go CLI
**File:** `cli/internal/stream/sse.go:51`
**Impact:** `bufio.NewScanner` defaults to 64KB max token size, but if the server sends very long SSE data lines, the scanner silently truncates. For a streaming display this is acceptable, but worth noting.

### H5. `Truncate` function in Go CLI operates on bytes, not runes
**File:** `cli/internal/output/format.go:80-84`
**Impact:** `len(s)` counts bytes, not characters. For multibyte UTF-8 strings, truncation at byte `maxLen-1` can split a character mid-sequence, producing invalid UTF-8 output.

```go
func Truncate(s string, maxLen int) string {
    if len(s) <= maxLen { return s }
    return s[:maxLen-1] + "..." // May split UTF-8
}
```

**Fix:** Use `[]rune(s)` for length check and slicing.

### H6. .NET SDK `_exporters` and `_processors` lists are read from multiple threads without consistent locking
**File:** `sdk-dotnet/src/AgentLens/AgentLensClient.cs:177-222`
**Impact:** The code takes a lock and creates a snapshot (good), but `AddExporter` and `AddProcessor` append to the lists under lock while other threads iterate via snapshot. This is actually correct as implemented -- the snapshot pattern prevents concurrent modification. However, the `_exporters` field is also read directly in `ActiveTrace.cs` indirectly via `AgentLensClient.EmitToExporters`. The current implementation is safe because it always snapshots under lock before iterating. No fix needed, but worth noting the pattern.

---

## MEDIUM Priority

### M1. Silent error swallowing across dashboard pages
**Files:** Multiple pages (`api-keys-page.tsx:26`, `alert-rules-page.tsx:35`, `alerts-list-page.tsx:21`, etc.)
**Impact:** Many `catch { /* ignore */ }` blocks silently swallow errors. Users get no feedback when delete, create, or toggle operations fail. This is a UX issue more than a security one.

**Fix:** Add toast/notification on caught errors, or at minimum log to console.

### M2. `any` type usage in error handlers
**Files:** `trace-detail-page.tsx:42`, `trace-replay-page.tsx:85`
**Impact:** Using `catch (e: any)` instead of proper type narrowing. Minor type-safety issue.

```ts
} catch (e: any) {
  setAutopsyError(e.message || 'Autopsy failed')
```

**Fix:** Use `catch (e: unknown)` with `e instanceof Error ? e.message : 'Failed'` pattern (used correctly elsewhere in the codebase).

### M3. CLI `traces list` parses response in wrong format
**File:** `cli/cmd/traces.go:92-103`
**Impact:** The CLI tries to parse the response as `[]map[string]interface{}` first, then falls back to `{data:[...]}`. But the actual server API returns `{traces: [...], total: N}` (based on dashboard's `TracesResponse` type). The CLI likely displays raw JSON instead of a table for the list command. Also uses field names like `trace_id`, `started_at` which may differ from actual server response (`id`, `created_at` per dashboard types).

**Fix:** Align CLI parsing with actual API response schema. Use wrapper struct: `{traces: [...], total: N}`, and map correct field names.

### M4. MCP integration uses `eval('require')` for dynamic import
**File:** `sdk-ts/src/integrations/mcp.ts:80`
**Impact:** Using `eval('require')` bypasses bundler static analysis and is flagged by security scanners. While this is intentional to keep the MCP SDK as optional, it may cause false positives in security audits.

```ts
Client = eval('require')("@modelcontextprotocol/sdk/client/index.js").Client;
```

**Fix:** Consider `await import()` with try/catch instead, or document the reason for eval usage.

### M5. Batch transport in TS SDK has no queue size limit
**File:** `sdk-ts/src/transport.ts:109-114`
**Impact:** When `_batchEnabled` is true and the server is unreachable, `_batchQueue` grows without bound since `flushBatch` catches and ignores fetch errors. This can cause memory growth in long-running applications.

**Fix:** Add a max queue size (e.g., 1000 items). When full, drop oldest entries.

### M6. .NET SDK static HttpClient never disposed
**File:** `sdk-dotnet/src/AgentLens/Transport.cs:14`
**Impact:** The `static readonly HttpClient` is intentionally shared (correct pattern per Microsoft guidance), but it never respects DNS changes since `HttpClient` caches DNS forever by default.

**Fix:** Consider using `IHttpClientFactory` or setting `SocketsHttpHandler.PooledConnectionLifetime` to handle DNS rotation.

### M7. .NET ActiveTrace `PopSpan` does not verify span identity
**File:** `sdk-dotnet/src/AgentLens/ActiveTrace.cs:50-55`
**Impact:** `PopSpan` takes a `SpanData` parameter but pops the stack regardless of whether the top matches the passed span. If spans are exited out of order (bug in user code), the stack silently corrupts.

```csharp
internal void PopSpan(SpanData span)
{
    lock (_lock)
    {
        if (_spanStack.Count > 0)
            _spanStack.Pop();  // Does not verify top == span.SpanId
    }
```

**Fix:** Add assertion: verify `_spanStack.Peek() == span.SpanId` before popping.

---

## LOW Priority

### L1. `fetchWithAuth` silently redirects on 401 without aborting the calling promise
**File:** `dashboard/src/lib/fetch-with-auth.ts:22-25`
**Impact:** On 401, the function clears the token and navigates to login, but still returns the Response object. The caller will then try to parse the 401 response body as valid JSON, likely resulting in a confusing error message instead of a clean redirect.

### L2. VS Code WebView `retainContextWhenHidden: true` may waste memory
**File:** `vscode-extension/src/trace-detail-webview.ts:34`
**Impact:** Keeps the webview DOM alive when the tab is hidden. Since `enableScripts: false`, the memory overhead is small, but unnecessary since the content is regenerated on each `show()` call.

### L3. Dashboard `useSSETraces` creates a new SSE connection per component instance
**File:** Multiple pages use `useSSETraces()` independently
**Impact:** `TracesListPage` and `TraceDetailPage` (via `useLiveTraceDetail`) each create their own EventSource connection to the same endpoint, doubling network connections. Consider a shared provider or singleton hook.

---

## Red-Team Analysis Results

| Question | Finding |
|----------|---------|
| 1. Can dashboard display malicious content from trace data? | **Low risk.** No `dangerouslySetInnerHTML` used. All trace data rendered via React JSX (auto-escaped). However, span `input`/`output` rendered in `<pre>` tags are auto-escaped by React. VS Code WebView uses proper `esc()` function. **Safe.** |
| 2. Can CLI commands be exploited via crafted trace IDs? | **Low risk.** `url.PathEscape` used in `traces show`. No shell execution of trace IDs. The trace ID is only used in URL paths and display output. **Safe.** |
| 3. Can VS Code extension leak credentials? | **Yes.** API key stored in plaintext `settings.json` (see C4). Additionally, the key is passed in HTTP headers but only to the configured endpoint. **Fix: use SecretStorage.** |
| 4. Can SDK crash user's application? | **No.** Both TS and .NET SDKs use fire-and-forget transport with caught exceptions. NoopSpanContext prevents crashes when used outside traces. Exporters are wrapped in try-catch. **Safe.** |

---

## Positive Observations

1. **No `dangerouslySetInnerHTML`** anywhere in the dashboard - all content is React-escaped
2. **VS Code WebView** has `enableScripts: false` and uses proper HTML escaping via `esc()` function
3. **SDK transport is fire-and-forget** with proper error catching - SDK can never crash host app
4. **CLI config file permissions** are correctly set: dir 0700, file 0600
5. **API key masking** in CLI `config show` command is well-implemented
6. **.NET SDK thread safety** uses proper lock-and-snapshot pattern for exporters
7. **AsyncLocalStorage / AsyncLocal** correctly used for context propagation in both TS and .NET SDKs
8. **NoopSpanContext** pattern in both SDKs prevents errors when tracing outside active trace
9. **Timer cleanup** in VS Code extension is thorough via `context.subscriptions`
10. **Consistent auth wrapping** via `fetchWithAuth` across most dashboard API clients

---

## Recommended Actions (Prioritized)

1. **[CRITICAL]** Fix auth bypass on `fetchAgents()` and `fetchAlertsSummary()` - switch to `fetchWithAuth()`
2. **[CRITICAL]** Address SSE auth gap - either document as intentional or implement authenticated SSE
3. **[CRITICAL]** Migrate VS Code extension API key storage to `SecretStorage` API
4. **[HIGH]** Fix `decodeURIComponent` missing on trace detail route hash parsing
5. **[HIGH]** Add response body size limits on CLI `io.ReadAll` calls
6. **[HIGH]** Fix `Truncate` function to handle UTF-8 properly in Go CLI
7. **[MEDIUM]** Replace silent `catch { /* ignore */ }` blocks with user-facing error feedback
8. **[MEDIUM]** Fix CLI trace list response parsing to match actual API schema
9. **[MEDIUM]** Add max queue size to TS SDK batch transport
10. **[LOW]** Consider singleton SSE connection for dashboard to avoid duplicate EventSource connections

---

## Metrics

| Component | Files | LOC (approx) | Critical | High | Medium | Low |
|-----------|-------|--------------|----------|------|--------|-----|
| Dashboard | 48 | ~2,800 | 2 | 2 | 2 | 2 |
| CLI (Go) | 8 | ~550 | 1 | 3 | 1 | 0 |
| VS Code Ext | 6 | ~430 | 1 | 0 | 0 | 1 |
| SDK-TS | 6 | ~480 | 0 | 0 | 2 | 0 |
| SDK-.NET | 12 | ~530 | 0 | 0 | 2 | 0 |
| **Total** | **80** | **~4,790** | **4** | **5** | **7** | **3** |

---

## Unresolved Questions

1. Does the server enforce auth on `/api/agents` and `/api/alerts/summary`? If unauthenticated access is by design, C1 can be downgraded.
2. Is the SSE endpoint intentionally unauthenticated (common for internal tools)? If yes, C2 can be downgraded to documented decision.
3. What is the maximum expected trace ID length and character set? This affects whether the hash routing issue (H1) is exploitable in practice.
4. Is the CLI's trace list response parsing (M3) untested? The field name mismatch (`trace_id` vs `id`) suggests it may have never worked correctly for table output.

---

**Status:** DONE
**Summary:** Full codebase review of 80 files across 5 components. Found 4 critical auth/credential issues, 5 high-priority robustness issues, 7 medium issues. No XSS vulnerabilities found. SDKs are well-hardened against host app crashes.
**Concerns:** The auth bypass on two dashboard API calls and the SSE auth gap are the most urgent findings. The CLI trace list parsing may be non-functional against the actual API schema.
