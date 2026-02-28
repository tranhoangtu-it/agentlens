# Phase 5: SDK Improvements & Integrations

## Context Links
- SDK source: `sdk/agentlens/` (467 LOC, 7 files)
- Tracer core: `sdk/agentlens/tracer.py` (218 LOC)
- Transport: `sdk/agentlens/transport.py` (38 LOC)
- Cost table: `sdk/agentlens/cost.py` (40 LOC)
- Existing integrations: `sdk/agentlens/integrations/` (langchain.py, crewai.py)
- pyproject.toml: `sdk/pyproject.toml`

## Overview
- **Priority**: P2
- **Status**: pending
- **Effort**: 5h
- **Description**: Expand SDK with OpenTelemetry-compatible export, add framework integrations for AutoGen, LlamaIndex, and Google ADK. Update cost table with latest models.

## Key Insights
- Current SDK is clean and minimal (decorator + context manager pattern)
- OTel integration = export AgentLens spans as OTel spans (not replace internal format)
- AutoGen v0.4+ uses event-driven architecture; needs event handler integration
- LlamaIndex uses callback manager pattern similar to LangChain
- Google ADK (Agent Development Kit) is newest; uses decorator-based instrumentation
- All integrations follow same pattern: hook into framework callbacks, create SpanData objects
- SDK is fully independent of dashboard/server changes — can develop in parallel

## Requirements

### Functional
- **OTel export**: Optional exporter that sends spans in OTel format alongside AgentLens format
- **AutoGen integration**: Auto-instrument AutoGen agent conversations and tool calls
- **LlamaIndex integration**: Callback handler for LLM calls, tool calls, retrieval
- **Google ADK integration**: Patch ADK agent runs and tool invocations
- **Updated cost table**: Add latest model pricing (Claude 4, GPT-4.5, Gemini 2, etc.)
- **Batch transport**: Option to batch multiple span posts in single HTTP request

### Non-Functional
- Zero overhead when integration not imported (lazy imports)
- All integrations are optional dependencies (extras in pyproject.toml)
- No breaking changes to existing public API

## Architecture

### New Files
```
sdk/agentlens/
  integrations/
    __init__.py              # (existing)
    langchain.py             # (existing, minor updates)
    crewai.py                # (existing, minor updates)
    autogen.py               # NEW
    llamaindex.py            # NEW
    google_adk.py            # NEW
  exporters/
    __init__.py
    otel.py                  # OpenTelemetry span exporter
  cost.py                    # Updated with latest models
  transport.py               # Add batch mode
```

### Integration Pattern (DRY)
All integrations follow the same pattern:
1. Try import framework — raise ImportError with install instructions if missing
2. Create callback/handler class that hooks into framework events
3. On framework event (llm_start, tool_start, etc.) create SpanData
4. Append SpanData to active trace via `_current_trace` context var

### OTel Export Architecture
```
AgentLens SDK
  ├── Internal spans (SpanData) → POST /api/traces (existing)
  └── OTel export (optional) → OTel Collector / Jaeger / etc.
      Uses opentelemetry-api to create OTel spans from SpanData
```

## Related Code Files

### Files to Modify
- `sdk/agentlens/cost.py` — add new model pricing
- `sdk/agentlens/transport.py` — add batch transport option
- `sdk/agentlens/tracer.py` — add exporter hook point
- `sdk/agentlens/__init__.py` — expose new configure options
- `sdk/pyproject.toml` — add new optional dependencies

### Files to Create
- `sdk/agentlens/integrations/autogen.py`
- `sdk/agentlens/integrations/llamaindex.py`
- `sdk/agentlens/integrations/google_adk.py`
- `sdk/agentlens/exporters/__init__.py`
- `sdk/agentlens/exporters/otel.py`

## Implementation Steps

### Step 1: Update cost table
1. Update `cost.py` with latest pricing:
   ```python
   # Add to MODEL_PRICES:
   "claude-sonnet-4": (3.00, 15.00),
   "claude-opus-4": (15.00, 75.00),
   "claude-haiku-4": (0.80, 4.00),
   "gpt-4.5-preview": (75.00, 150.00),
   "gpt-4.1": (2.00, 8.00),
   "gpt-4.1-mini": (0.40, 1.60),
   "gpt-4.1-nano": (0.10, 0.40),
   "gemini-2.0-flash": (0.10, 0.40),
   "gemini-2.0-pro": (1.25, 10.00),
   "deepseek-v3": (0.27, 1.10),
   "deepseek-r1": (0.55, 2.19),
   ```

### Step 2: Batch transport
1. Update `transport.py`:
   - Add `_batch_queue` (list) and `_batch_timer` (threading.Timer)
   - `post_trace()` can optionally queue instead of send immediately
   - `flush_batch()` sends all queued traces in single POST
   - Auto-flush every 5s or when queue hits 10 items
   - New endpoint needed: server `POST /api/traces/batch` (or reuse existing with array body)

### Step 3: AutoGen integration
1. Create `integrations/autogen.py`:
   ```python
   # AutoGen v0.4 uses AgentChat with event-driven messages
   # Hook into: ConversableAgent.on_message, tool execution
   from agentlens.tracer import SpanData, _current_trace, _now_ms

   def patch_autogen():
       """Monkey-patch AutoGen ConversableAgent for auto-instrumentation."""
       import autogen
       # Patch ConversableAgent.generate_reply
       # Patch ConversableAgent._execute_function
   ```
2. Follow same pattern as crewai.py: patch methods, create spans

### Step 4: LlamaIndex integration
1. Create `integrations/llamaindex.py`:
   ```python
   # LlamaIndex uses CallbackManager with event handlers
   from llama_index.core.callbacks.base import BaseCallbackHandler

   class AgentLensCallbackHandler(BaseCallbackHandler):
       """Drop-in LlamaIndex callback for AgentLens."""
       def on_event_start(self, event_type, payload, event_id, **kwargs): ...
       def on_event_end(self, event_type, payload, event_id, **kwargs): ...
   ```
2. Map LlamaIndex event types to AgentLens span types:
   - `CBEventType.LLM` -> `llm_call`
   - `CBEventType.RETRIEVE` -> `tool_call`
   - `CBEventType.QUERY` -> `agent_run`

### Step 5: Google ADK integration
1. Create `integrations/google_adk.py`:
   ```python
   # Google ADK uses decorator-based agents
   # Hook into: Agent.__call__, ToolContext
   def patch_google_adk():
       """Monkey-patch Google ADK for auto-instrumentation."""
       from google.adk import Agent
       # Patch Agent.__call__ or Agent.run
   ```
2. Map ADK concepts to spans:
   - Agent execution -> `agent_run`
   - Tool invocation -> `tool_call`
   - LLM generation -> `llm_call`

### Step 6: OpenTelemetry exporter
1. Create `exporters/otel.py`:
   ```python
   from opentelemetry import trace as otel_trace
   from opentelemetry.sdk.trace import TracerProvider

   class AgentLensOTelExporter:
       """Export AgentLens spans as OpenTelemetry spans."""
       def __init__(self, service_name="agentlens"):
           self.tracer = otel_trace.get_tracer(service_name)

       def export_span(self, span_data: SpanData):
           with self.tracer.start_as_current_span(span_data.name) as otel_span:
               otel_span.set_attribute("agentlens.type", span_data.type)
               otel_span.set_attribute("agentlens.cost_usd", span_data.cost.get("usd", 0))
               # ... map all fields
   ```
2. Hook into `ActiveTrace.flush()` — after posting to AgentLens, also export to OTel

### Step 7: Update pyproject.toml
1. Add optional dependencies:
   ```toml
   [project.optional-dependencies]
   langchain = ["langchain-core>=0.2"]
   crewai = ["crewai>=0.51"]
   autogen = ["autogen-agentchat>=0.4"]
   llamaindex = ["llama-index-core>=0.11"]
   google-adk = ["google-adk>=0.3"]
   otel = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
   all = ["agentlens-observe[langchain,crewai,autogen,llamaindex,google-adk,otel]"]
   ```

## Todo List
- [ ] Update `sdk/agentlens/cost.py` with latest model pricing
- [ ] Add batch transport option to `sdk/agentlens/transport.py`
- [ ] Create `sdk/agentlens/integrations/autogen.py`
- [ ] Create `sdk/agentlens/integrations/llamaindex.py`
- [ ] Create `sdk/agentlens/integrations/google_adk.py`
- [ ] Create `sdk/agentlens/exporters/__init__.py`
- [ ] Create `sdk/agentlens/exporters/otel.py`
- [ ] Add exporter hook to `sdk/agentlens/tracer.py`
- [ ] Update `sdk/pyproject.toml` with new optional deps
- [ ] Update `sdk/README.md` with integration examples
- [ ] Test each integration with minimal example script

## Success Criteria
- `pip install agentlens-observe[autogen]` and AutoGen runs auto-traced
- `pip install agentlens-observe[llamaindex]` and LlamaIndex queries auto-traced
- `pip install agentlens-observe[google-adk]` and ADK agents auto-traced
- `pip install agentlens-observe[otel]` and spans export to Jaeger/Zipkin
- Cost table covers top 20 LLM models with accurate 2026 pricing
- No import errors when optional deps not installed

## Risk Assessment
- **Risk**: Framework APIs change between versions — **Mitigation**: Pin minimum versions, use try/except for API variations
- **Risk**: AutoGen v0.4 API is not stable yet — **Mitigation**: Target stable release, add version check
- **Risk**: OTel adds cold-start overhead — **Mitigation**: Lazy import, only initialize when `configure(otel=True)` called

## Security Considerations
- No credentials stored in SDK; OTel exporter uses standard OTel env vars
- Framework integrations only read data, never modify agent behavior
