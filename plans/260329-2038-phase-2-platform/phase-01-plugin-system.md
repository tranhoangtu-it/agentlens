# Phase 2A: Plugin System

## Overview
- **Priority:** High — foundational for Eval and future Replay Sandbox
- **Status:** pending
- **Effort:** ~2 days

## Architecture

### SDK-Side Plugins (Python + TypeScript)

Add `SpanProcessor` protocol alongside existing `SpanExporter`:

```python
# sdk/agentlens/plugins.py
class SpanProcessor(Protocol):
    def on_start(self, span: SpanData) -> None: ...
    def on_end(self, span: SpanData) -> None: ...
```

Register via `configure(processors=[...])`. Called in `tracer.py` push_span/pop_span.

### Server-Side Plugins

```python
# server/plugin_protocol.py
class ServerPlugin(Protocol):
    name: str
    def on_trace_created(self, trace: Trace, spans: list[Span]) -> None: ...
    def on_trace_completed(self, trace: Trace, spans: list[Span]) -> None: ...
    def register_routes(self, app: FastAPI) -> None: ...
```

Auto-discover from `server/plugins/` directory at startup via `plugin_loader.py`.

## Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `sdk/agentlens/plugins.py` | ~30 | SpanProcessor protocol definition |
| `server/plugin_protocol.py` | ~30 | ServerPlugin protocol definition |
| `server/plugin_loader.py` | ~60 | Auto-discover + load plugins from server/plugins/ |
| `server/plugins/__init__.py` | ~1 | Package marker |
| `sdk/tests/test_plugins.py` | ~60 | SpanProcessor tests |
| `server/tests/test_plugin_loader.py` | ~50 | Plugin discovery tests |

## Files to Modify

| File | Change |
|------|--------|
| `sdk/agentlens/tracer.py` | Call processors on_start/on_end in push_span/pop_span |
| `sdk/agentlens/__init__.py` | Export `add_processor` |
| `server/main.py` | Load plugins in lifespan, call hooks in trace ingestion |
| `server/storage.py` | Add hook points after create_trace/add_spans |

## Implementation Steps

1. Create `sdk/agentlens/plugins.py` — SpanProcessor protocol
2. Modify `sdk/agentlens/tracer.py` — add `_processors` list, call on push/pop
3. Export `add_processor` in `__init__.py`
4. Create `server/plugin_protocol.py` — ServerPlugin protocol
5. Create `server/plugin_loader.py` — discover `.py` files in `server/plugins/`
6. Create `server/plugins/__init__.py`
7. Modify `server/main.py` — load plugins in lifespan, store in app.state
8. Modify `server/main.py` — call `on_trace_created`/`on_trace_completed` in ingestion endpoints
9. Write tests
10. Run pytest

## Key Details

- **SDK processors:** Wrap in try/except like exporters — never break user code
- **Server plugin loading:** `importlib.import_module()` on each `.py` in plugins/
- **Plugin must expose:** `plugin = MyPlugin()` module-level instance
- **No hot-reload:** Plugins loaded once at startup (KISS)
- **TypeScript SDK:** Add `SpanProcessor` interface + `addProcessor()` to mirror Python

## Success Criteria
- [ ] SpanProcessor called on span start/end
- [ ] Server plugins auto-discovered and hooks called
- [ ] Existing tests still pass (no regression)
- [ ] Plugin errors don't crash app
