# AgentLens Server + SDK Codebase Review

**Reviewer:** code-reviewer | **Date:** 2026-03-30
**Scope:** Full codebase scan of `server/` (38 .py files, ~2400 LOC) and `sdk/agentlens/` (13 .py files, ~1100 LOC)
**Mode:** Adversarial / production-readiness

---

## CRITICAL Issues

### C1. Open Registration Endpoint — No Rate Limiting or Invite-Only Guard
- **File:** `server/auth_routes.py:20-29`
- **Description:** `POST /api/auth/register` is fully open. Any internet caller can create unlimited accounts. Combined with no rate limiting anywhere, this enables resource exhaustion (DB fill, compute abuse via LLM eval endpoints).
- **Impact:** Denial of service, cost abuse (users trigger LLM calls with their own keys, but storage/DB is shared).
- **Fix:** Add rate limiting middleware (e.g., `slowapi`) and/or make registration invite-only or disable via env flag.

### C2. SSRF Time-of-Check-Time-of-Use in Webhook URL Validation
- **File:** `server/alert_notifier.py:31-66, 79-112`
- **Description:** `validate_webhook_url()` resolves the hostname and checks IPs, but the actual HTTP request in `_send()` re-resolves DNS independently via `urllib.request.urlopen()`. An attacker with DNS control can return a safe IP during validation but a private IP during the actual request (DNS rebinding attack).
- **Impact:** SSRF to internal services.
- **Fix:** Resolve DNS once, pin the IP, and connect to the resolved IP directly (or use a library that supports pinning). Alternatively, use an HTTP client that allows pre-resolved addresses.

### C3. Webhook URL Not Validated on AlertRule Creation/Update
- **File:** `server/alert_routes.py:28-35`, `server/alert_models.py:78`
- **Description:** `_validate_rule()` checks metric/operator/mode but never calls `validate_webhook_url()` on the `webhook_url` field. SSRF validation only happens at fire time. A user can store any URL (including `file://`, `ftp://`, etc.) and the scheme check only happens when the alert fires.
- **Impact:** Stored SSRF vector. The URL bypasses validation until alert fires; if validation logic changes later, old stored URLs may slip through.
- **Fix:** Call `validate_webhook_url()` during rule creation/update in `_validate_rule()`.

### C4. SSE Bus `publish_alert_sse` Broadcasts to All Users
- **File:** `server/alert_notifier.py:68-76`
- **Description:** `publish_alert_sse()` calls `bus.publish()` without passing `user_id`. This means ALL connected SSE subscribers see every user's alert events. This is a **cross-tenant data leak**.
- **Impact:** User A sees User B's alert rule names, agent names, metrics, and alert messages in real-time.
- **Fix:** Pass `user_id=event.user_id` (or the rule's user_id) to `bus.publish()`.

### C5. Alert Evaluator Baseline Query Missing Tenant Isolation
- **File:** `server/alert_evaluator.py:153-171`
- **Description:** `_get_baseline_avg()` filters by `agent_name` and `status` but **does not filter by `user_id`**. A user's relative alert threshold is computed using other users' traces that share the same `agent_name`.
- **Impact:** Cross-tenant data leakage (metric values inferred from other tenants), incorrect alert thresholds.
- **Fix:** Add `Trace.user_id == user_id` filter to the baseline query. Pass `user_id` through from `_evaluate_single_rule`.

---

## HIGH Priority

### H1. Detached SQLModel Objects Returned Outside Session Scope
- **File:** `server/storage.py:187-197`, `server/auth_storage.py:45-49`, and many others
- **Description:** Almost every storage function returns SQLModel objects after the `Session` context manager closes. Accessing lazy-loaded relationships on these detached objects will raise `DetachedInstanceError`. Currently there are no relationships defined so this works, but it's fragile and will break the moment any FK relationship is added.
- **Impact:** Latent bug; will cause 500 errors when relationships are introduced.
- **Fix:** Either use `expire_on_commit=False` on the engine, or convert to dicts/Pydantic models within the session scope.

### H2. Trace Upsert Race Condition — Delete + Re-Insert Without Locking
- **File:** `server/storage.py:89-102`
- **Description:** `create_trace()` does DELETE + INSERT in a single session but without any explicit locking. Two concurrent requests for the same `trace_id` could interleave: both read the existing trace, both delete, one inserts, the other also inserts (or one deletes the other's insert). SQLite WAL mitigates this somewhat due to write serialization, but PostgreSQL does not.
- **Impact:** Duplicate traces or lost spans in PostgreSQL deployments.
- **Fix:** Use `SELECT ... FOR UPDATE` or `INSERT ... ON CONFLICT DO UPDATE` (upsert) instead of delete-then-insert.

### H3. OTel Ingestion Accepts Arbitrary Dict — No Schema Validation
- **File:** `server/main.py:143-144`
- **Description:** `ingest_otel_traces` declares `body: dict` with no Pydantic model. Any JSON payload is accepted. `map_otlp_request` then traverses it with `.get()` calls that silently swallow malformed data but could also produce unexpected DB state.
- **Impact:** Malformed payloads can insert spans with empty span_ids (empty string as PK), potentially causing PK conflicts or data corruption.
- **Fix:** Create a Pydantic model for OTLP input (at least validate `resourceSpans` is a list). Add guards in `map_otlp_request` for empty `span_id`.

### H4. Batch Transport Missing Auth Headers
- **File:** `sdk/agentlens/transport.py:112-119`
- **Description:** `flush_batch()` posts to `/api/traces/batch` but does **not** include `_auth_headers()` in the request. The `_send()` function inside `flush_batch` builds headers without `**_auth_headers()`, unlike immediate mode which includes them.
- **Impact:** All batch-mode trace submissions will fail with 401 when server requires authentication. Feature is silently broken.
- **Fix:** Add `headers={"Content-Type": "application/json", **_auth_headers()}` to the batch POST request.

### H5. Batch Endpoint Does Not Exist on Server
- **File:** `sdk/agentlens/transport.py:110`
- **Description:** Batch transport POSTs to `/api/traces/batch` but no such endpoint is defined on the server. This means the entire batch feature silently discards all traces.
- **Impact:** Data loss when batch mode is enabled. No user-visible error (fire-and-forget logs at debug level).
- **Fix:** Either implement `/api/traces/batch` on the server, or remove/mark batch mode as experimental with a clear warning.

### H6. No Input Length Validation on Span/Trace Fields
- **File:** `server/models.py:61-77`, `server/storage.py:40-103`
- **Description:** `SpanIn` has no length constraints on `input`, `output`, `name`, or `type` fields. A single span could have a 100MB `input` string. The server stores these as-is (SQLite TEXT has no limit; PostgreSQL TEXT likewise).
- **Impact:** Single API call can cause OOM or fill disk. DoS vector.
- **Fix:** Add `max_length` constraints on Pydantic models: `name` (256), `type` (64), `input`/`output` (e.g., 1MB or 64KB depending on requirements).

### H7. Global Mutable State in SDK Not Thread-Safe
- **File:** `sdk/agentlens/tracer.py:47-48`
- **Description:** `_exporters` and `_processors` are plain `list` objects. `add_exporter()` and `add_processor()` append without locking. If called from multiple threads during initialization, the list could be corrupted (though CPython's GIL makes this unlikely for append, iterating while appending can skip items or raise).
- **Impact:** Low probability but possible data race in multi-threaded initialization.
- **Fix:** Use `threading.Lock` for mutations, or document that `configure`/`add_exporter`/`add_processor` must be called before any tracing begins.

---

## MEDIUM Priority

### M1. Prompt Version Race Condition
- **File:** `server/prompt_storage.py:69-97`
- **Description:** `add_version()` uses `SELECT MAX(version)` then `INSERT` with `next_version = max + 1`. Despite using DB-level MAX, two concurrent requests can both read the same max and try to insert the same version number. The `UNIQUE` index on `(prompt_id, version)` will cause one to fail, but the error is caught generically and returns `None` (which maps to 404 "Prompt template not found").
- **Impact:** Misleading error on concurrent version creation.
- **Fix:** Catch `IntegrityError` specifically and retry with incremented version, or use DB sequence/auto-increment.

### M2. Default Admin Password "changeme" Accepted in Production
- **File:** `server/auth_seed.py:15, 23-24`
- **Description:** Warns at log level but doesn't block. If `AGENTLENS_ADMIN_PASSWORD` is not set, "changeme" is used and the admin account has full access.
- **Impact:** Any attacker who can reach the login endpoint can log in as admin.
- **Fix:** In production mode, refuse to start if admin password is the default, or require `AGENTLENS_ADMIN_PASSWORD` to be set.

### M3. Email Validation Missing
- **File:** `server/auth_models.py:51-52`, `server/auth_routes.py:21`
- **Description:** `RegisterIn.email` is typed as `str` with no format validation. Users can register with `email=""`, `email="<script>..."`, or any arbitrary string.
- **Impact:** Stored XSS if email is rendered unescaped in a frontend; invalid data in DB.
- **Fix:** Use Pydantic `EmailStr` validator from `pydantic[email]`.

### M4. SQL Injection Surface in `_migrate_orphan_data`
- **File:** `server/auth_seed.py:48-53`
- **Description:** Uses f-string for table name: `f"UPDATE {table} SET ..."`. The table names are hardcoded constants ("trace", "alert_rule", "alert_event"), so this is not exploitable today, but if this pattern is copied or table names become dynamic, it becomes a SQL injection.
- **Impact:** Currently safe, but risky pattern.
- **Fix:** Use `text(f"UPDATE {table} ...")` with a whitelist check (which is already implicitly done by the hardcoded list).

### M5. OTel Exporter Mutates Span Metadata In-Place
- **File:** `sdk/agentlens/exporters/otel.py:162`
- **Description:** `span.metadata.pop("logs", None)` mutates the original `SpanData.metadata` dict. If multiple exporters process the same span, exporters after the OTel one will not see the `logs` key.
- **Impact:** Data loss for downstream exporters.
- **Fix:** Copy metadata before mutation: `meta = dict(span.metadata)`.

### M6. Unbounded SSE Subscriber Memory Growth
- **File:** `server/sse.py:31`
- **Description:** Each subscriber gets a `Queue(maxsize=100)`. Dead queues are only cleaned up on `QueueFull`, not on client disconnect without `finally` block execution. If a client disconnects uncleanly (network drop), the `finally` block in `subscribe()` may not run, leaving zombie queues.
- **Impact:** Memory leak under connection churn.
- **Fix:** Add periodic cleanup of stale subscribers or use weakrefs.

### M7. `create_trace` Allows User-Controlled `trace_id` as Primary Key
- **File:** `server/storage.py:40-41`, `server/main.py:91`
- **Description:** The `trace_id` comes directly from the client request body (`TraceIn.trace_id`). This is the PK. A user could overwrite their own existing trace by sending the same `trace_id` (the upsert logic deletes and re-inserts). More importantly, user A cannot overwrite user B's trace (tenant check passes), but the user controls their own PK namespace.
- **Impact:** Low — user can only affect their own data. But client-controlled PKs make it harder to reason about data integrity.
- **Fix:** Consider server-generated UUIDs for PKs, or document this as intentional (trace_id from SDK).

### M8. Crypto Key Derived from JWT Secret — Key Rotation Breaks Encrypted Values
- **File:** `server/crypto.py:18-27`
- **Description:** The Fernet encryption key is derived from `AGENTLENS_JWT_SECRET`. If the JWT secret is rotated (e.g., for security), all stored encrypted API keys become undecryptable. `decrypt_value` returns `None` but doesn't alert the user.
- **Impact:** Users lose their stored LLM API keys after a JWT secret rotation with no clear error path.
- **Fix:** Use a separate `AGENTLENS_ENCRYPTION_KEY` env var, or at minimum document this coupling.

---

## LOW Priority

### L1. Health Endpoint Leaks Internal State
- **File:** `server/main.py:84`
- **Description:** Returns `{"status": "degraded", "db": "error"}` but does not include the exception details (good). However, `status: "degraded"` vs `"ok"` reveals backend health to unauthenticated callers.
- **Impact:** Minimal — health endpoints are commonly unauthenticated.

### L2. Cost Table Prefix Matching Can Be Ambiguous
- **File:** `sdk/agentlens/cost.py:58-63`
- **Description:** Fuzzy matching `if key.startswith(k) or k.startswith(key)` can match wrong models. E.g., `"gpt-4"` startswith `"gpt-4"` matches `"gpt-4-turbo"`, `"gpt-4o"`, `"gpt-4o-mini"`, `"gpt-4.1"` etc. The first match wins, depending on dict iteration order.
- **Impact:** Slightly wrong cost calculations for ambiguous model names.
- **Fix:** Sort keys by length descending before matching, or use exact match only with documented model aliases.

### L3. OTel Exporter `end()` Called Twice
- **File:** `sdk/agentlens/exporters/otel.py:123-179`
- **Description:** The `with self._tracer.start_as_current_span(...)` context manager calls `end()` on exit. Then line 177 explicitly calls `otel_span.end(end_time=end_ns)`. This double-end may log a warning in some OTel implementations.
- **Impact:** Noisy logs, no data corruption.
- **Fix:** Don't use context manager; use `start_span()` instead and call `end()` once with explicit timestamp.

### L4. Integration Monkey-Patches Not Reversible
- **File:** All `sdk/agentlens/integrations/*.py`
- **Description:** `patch_crewai()`, `patch_autogen()`, etc. store `_patched = True` but don't save original methods for unpatch. Testing/cleanup is impossible.
- **Impact:** Minor — mainly affects testing.

### L5. `ActiveTrace.spans` List Grows Without Bound
- **File:** `sdk/agentlens/tracer.py:111`
- **Description:** In streaming mode, spans are sent immediately via `flush_span` but remain in `self.spans`. They're also re-sent in the final `flush()` call. Traces with thousands of spans will use excessive memory.
- **Impact:** Memory pressure for long-running agents in streaming mode.
- **Fix:** Clear spans after streaming flush, or skip full-trace flush in streaming mode.

---

## Red-Team Analysis Results

### 1. Can an authenticated user access another user's data?
**YES** — Two confirmed vectors:
- **C4:** SSE alert events broadcast to all subscribers (cross-tenant leak)
- **C5:** Baseline computation uses cross-tenant trace data

All other CRUD endpoints properly filter by `user_id`. The `get_trace`, `get_trace_pair`, `add_spans_to_trace` functions all check `user_id`. Route-level auth is consistent (all endpoints use `Depends(get_current_user)`).

### 2. Can SDK crash the user's application?
**NO** — Good defensive design. All transport is fire-and-forget in daemon threads. Exceptions in exporters/processors are caught. `_NoopSpanContext` prevents errors when tracing is inactive. The only risk is the `ImportError` raised by optional integration imports, which is expected behavior.

### 3. Can malformed input cause server errors?
**YES** — Several vectors:
- **H3:** OTel endpoint accepts `dict` with no validation, can produce empty-string PKs
- **H6:** No length limits on span content, enables OOM
- **M3:** No email format validation

### 4. Can concurrent requests corrupt state?
**YES** — Two confirmed vectors:
- **H2:** Trace upsert race condition (DELETE + INSERT without locking) on PostgreSQL
- **M1:** Prompt version race condition (MAX + INSERT)

---

## Positive Observations

1. **Consistent tenant isolation** across all major CRUD operations (traces, alerts, prompts, evals, replay sessions) — the pattern of checking `user_id` is applied uniformly
2. **SSRF prevention** for webhooks is well-designed (blocks RFC-1918, loopback, link-local, IPv6 ULA)
3. **Good error handling** in plugin system — individual plugin failures don't crash the server
4. **SDK non-intrusive design** — fire-and-forget transport, noop contexts, caught exceptions
5. **API key hashing** with SHA-256 (not stored in plaintext), bcrypt for passwords
6. **Proper parameterized queries** via SQLModel/SQLAlchemy throughout (no raw string interpolation for user data)
7. **Sort column whitelist** in `list_traces` prevents SQL injection via sort parameter
8. **WAL mode** enabled for SQLite for better concurrency

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 5 |
| HIGH | 7 |
| MEDIUM | 8 |
| LOW | 5 |

**Top 3 actions before production deployment:**
1. Fix cross-tenant data leaks (C4, C5)
2. Add rate limiting and input size validation (C1, H6)
3. Fix batch transport (H4, H5) or disable the feature

**Status:** DONE
**Summary:** Full adversarial review of server (38 files) and SDK (13 files) completed. Found 5 critical issues (2 cross-tenant leaks, 1 SSRF TOCTOU, 1 stored SSRF, 1 open registration), 7 high-priority issues, and 13 medium/low issues.
**Concerns:** C4 and C5 are actively exploitable cross-tenant data leaks that should be fixed before any multi-user deployment.
