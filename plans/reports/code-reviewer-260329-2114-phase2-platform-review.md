# Code Review: Phase 2 Platform Features

**Scope:** Plugin System, Prompt Versioning, LLM-as-Judge Eval
**Files:** 11 server files, 1 SDK file (tracer.py)
**Focus:** Security, error handling, correctness, code quality

---

## Critical Issues

### 1. [CRITICAL] Prompt version auto-increment race condition — `prompt_storage.py:64-86`

`add_version()` reads `template.latest_version`, increments in Python, then writes back. Two concurrent requests can read the same version number, both increment to N+1, and one silently overwrites the other. The unique index `ix_pv_prompt_version` will cause one to fail with an unhandled IntegrityError that crashes the request with a 500.

**Fix:** Use `SELECT ... FOR UPDATE` or a DB-level `latest_version = latest_version + 1` with `RETURNING`:
```python
from sqlalchemy import text
session.execute(
    text("UPDATE prompt_template SET latest_version = latest_version + 1 WHERE id = :id RETURNING latest_version"),
    {"id": prompt_id}
)
```
Or catch `IntegrityError` and retry.

### 2. [CRITICAL] Plugin code execution — arbitrary code loading with no sandboxing — `plugin_loader.py:38`

`importlib.import_module(module_name)` executes arbitrary Python from `server/plugins/`. Any file dropped there runs with server process privileges. The `register_routes(app)` call at line 43 gives plugins full access to the FastAPI app, including ability to override auth middleware.

**Mitigations needed:**
- Document that `plugins/` directory must be write-protected in production
- Consider allowlisting plugin modules via config rather than auto-discovery
- At minimum, validate `isinstance(plugin, ServerPlugin)` before calling `register_routes` (the Protocol check exists but is never enforced — line 39 just checks for `plugin` attribute)

### 3. [CRITICAL] Eval run silently skips invalid traces — `eval_routes.py:83-93`

When `get_trace()` returns None (line 86) or `run_eval()` raises `LLMProviderError` (line 92-93), the loop `continue`s without any error reporting to the caller. A user could submit 10 trace IDs, all fail, and get back `{"runs": [], "count": 0}` with 200 status — indistinguishable from success with no traces.

**Fix:** Collect errors per trace_id and return them:
```python
errors = []
# in the loop:
errors.append({"trace_id": trace_id, "error": "Trace not found"})
# response:
return {"runs": results, "count": len(results), "errors": errors}
```

---

## High Priority (Warning)

### 4. [WARNING] `_plugins` global list is not thread-safe — `plugin_loader.py:15,27`

`_plugins` is a module-level mutable list. `load_plugins()` resets it with `_plugins = []`, while `notify_trace_*` iterates it. If `load_plugins()` is called during a request that's iterating plugins (e.g., hot-reload), you get undefined behavior. FastAPI with uvicorn workers usually means single-thread-per-worker, but with `--workers N` this is still a concern.

**Fix:** Use a threading lock or make `_plugins` immutable (tuple) after load.

### 5. [WARNING] `json_mode` only enabled for OpenAI — `eval_runner.py:82-83`

`json_mode=(provider == "openai")` means Anthropic and Gemini get no JSON enforcement. The LLM can return free-text, causing the JSON parse fallback (line 106-111) to trigger, which returns `score: 0.0` — a valid-looking but meaningless result. Users won't know their evals are silently failing for non-OpenAI providers.

**Impact:** Eval scores systematically biased to 0.0 for Anthropic/Gemini users.

**Fix:** For Anthropic, append "Respond ONLY with valid JSON" to the system prompt (already present in user prompt but worth reinforcing). For Gemini, use `responseMimeType: "application/json"` in generationConfig.

### 6. [WARNING] Eval runner blocks request thread — `eval_routes.py:83-93`

The eval endpoint loops over up to 10 traces, each making a synchronous HTTP call to an LLM provider with 60s timeout. Worst case: 10 * 60s = 600s blocking a FastAPI worker thread. This will cause connection timeouts for other users.

**Fix:** Run evals as background tasks (`BackgroundTasks`) or use async with `httpx.AsyncClient`.

### 7. [WARNING] `update_criteria` allows setting arbitrary attributes — `eval_storage.py:53-54`

`setattr(c, key, val)` with `data` coming from `body.model_dump()`. While Pydantic filters the fields, the `EvalCriteriaUpdate` model includes `Optional` fields — if someone passes `user_id` or `id` through API extension/middleware bypass, they could overwrite ownership. Currently safe due to Pydantic schema, but fragile.

**Fix:** Explicitly allowlist mutable fields:
```python
MUTABLE_FIELDS = {"name", "description", "rubric", "score_type", "agent_name", "auto_eval", "enabled"}
for key, val in data.items():
    if key in MUTABLE_FIELDS and val is not None:
        setattr(c, key, val)
```

### 8. [WARNING] No input length validation on rubric/content — `eval_models.py:17`, `prompt_models.py:63`

`rubric: str` and `content: str` accept unbounded strings. A malicious/accidental multi-MB rubric gets stored in DB and then injected into every LLM judge prompt, causing excessive token costs.

**Fix:** Add `max_length` to Pydantic models:
```python
rubric: str = Field(..., max_length=10000)
content: str  # add max_length=50000 or similar
```

---

## Medium Priority (Info)

### 9. [INFO] Detached ORM objects returned from sessions — `eval_storage.py:23`, `prompt_storage.py:27`

Objects are returned after `session.refresh()` but the session is closed (context manager exit). Accessing lazy-loaded relationships will raise `DetachedInstanceError`. Currently no relationships defined, so safe — but will break silently if relationships are added later.

### 10. [INFO] `_exporters` and `_processors` are global mutable lists — `tracer.py:47-48`

`add_exporter()` and `add_processor()` append to module-level lists with no deduplication or removal mechanism. Calling `configure()` multiple times (e.g., in tests) accumulates duplicate processors. No `clear_processors()` or `remove_processor()` API exists.

### 11. [INFO] Missing `isinstance` check on plugin protocol — `plugin_loader.py:39-43`

The `ServerPlugin` Protocol is `@runtime_checkable` but never actually checked. A plugin missing `on_trace_created` would crash on first trace, not at load time.

**Fix:** Add after line 39:
```python
if not isinstance(plugin, ServerPlugin):
    logger.warning("Plugin %s does not implement ServerPlugin protocol", module_name)
    continue
```

### 12. [INFO] Prompt template name uniqueness error not user-friendly — `prompt_storage.py:18-27`

The unique index `ix_prompt_user_name` will raise an `IntegrityError` if a user creates two prompts with the same name. This surfaces as an unhandled 500 error.

**Fix:** Catch `IntegrityError` in `create_prompt` and raise a descriptive error, or check existence first.

### 13. [INFO] `EvalCriteriaIn` missing `user_id` field — `eval_models.py:52-60`

`user_id` is injected at the route layer (line 40 of eval_routes.py). This is correct design (trust boundary), but `create_criteria` at `eval_storage.py:18` does `EvalCriteria(id=..., **data)` — if caller forgets `user_id`, the DB will accept the record with `user_id=""` (no NOT NULL constraint visible). Add explicit NOT NULL or validation.

---

## Positive Observations

- **Tenant isolation** consistently enforced: all storage functions check `user_id` ownership
- **Plugin error isolation** well-implemented: try/except in `notify_trace_*` prevents one plugin from crashing others
- **Eval score clamping** at `eval_runner.py:97-100` prevents out-of-range scores
- **API key never logged**: `llm_provider.py` handles keys without logging them
- **Auth on all routes**: every endpoint uses `Depends(get_current_user)`
- **Prompt diff** implementation clean and correct using `difflib`

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 3 |
| Warning | 5 |
| Info | 5 |

**Top 3 actions:**
1. Fix prompt version race condition (data corruption risk)
2. Add error reporting to eval run endpoint (silent failures)
3. Make eval execution async or background (worker exhaustion)

---

**Status:** DONE
**Summary:** Reviewed Phase 2 platform features (plugin system, prompt versioning, eval runner). Found 3 critical issues: prompt version race condition, plugin sandboxing gaps, and silent eval failures. 5 warnings around thread safety, JSON mode gaps, and input validation.
**Concerns/Blockers:** None blocking — all issues have clear fixes.
