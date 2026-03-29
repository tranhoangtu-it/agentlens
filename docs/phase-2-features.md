# AgentLens Phase 2 Features — Plugin System, Prompts, Evaluation

**Status:** Implemented in v0.8.0 | **Release:** March 2026

## Overview

Phase 2 introduces three major systems:
1. **Plugin System** — Extensible server hooks for trace lifecycle events
2. **Prompt Versioning** — Manage and version control prompt templates
3. **LLM-as-Judge Evaluation** — Assess agent outputs using LLM-based scoring criteria

## 1. Plugin System

### Purpose
Enable third-party extensions to hook into trace lifecycle events without modifying core AgentLens code.

### Architecture

**Protocol** (`server/plugin_protocol.py`)
```python
@runtime_checkable
class ServerPlugin(Protocol):
    name: str

    def on_trace_created(self, trace_id: str, agent_name: str, span_count: int) -> None:
        """Called immediately after trace ingestion."""
        ...

    def on_trace_completed(self, trace_id: str, agent_name: str) -> None:
        """Called when trace status becomes 'completed'."""
        ...

    def register_routes(self, app: FastAPI) -> None:
        """Register custom API routes. Called once at startup."""
        ...
```

**Auto-Discovery** (`server/plugin_loader.py`)
- Scans `server/plugins/` directory on startup
- Each `.py` file must expose module-level `plugin` instance
- Loads plugins and calls `register_routes(app)` for each
- Non-fatal error handling: plugin exceptions logged, server continues

### Usage

1. Create `server/plugins/my_plugin.py`:
```python
from fastapi import APIRouter
from plugin_protocol import ServerPlugin

class MyPlugin:
    name = "my_plugin"

    def on_trace_created(self, trace_id, agent_name, span_count):
        print(f"Trace {trace_id} created for {agent_name}")

    def on_trace_completed(self, trace_id, agent_name):
        print(f"Trace {trace_id} completed")

    def register_routes(self, app):
        router = APIRouter()

        @router.get("/api/plugins/my_plugin/status")
        def status():
            return {"status": "ok"}

        app.include_router(router)

plugin = MyPlugin()
```

2. Plugin is auto-loaded on server startup
3. Hooks are called by `plugin_loader.notify_trace_created()` and `notify_trace_completed()`

### Integration Points
- `create_trace()` in `server/storage.py` calls `notify_trace_created(trace_id, agent_name, span_count)`
- Trace status update to 'completed' calls `notify_trace_completed(trace_id, agent_name)`

## 2. Prompt Versioning

### Purpose
Manage prompt templates with version history, enabling experimentation and rollback of prompt changes.

### Data Model

**PromptTemplate**
- `id` — UUID
- `user_id` — Owner
- `name` — Template name (unique per user)
- `latest_version` — Current version number
- `created_at`, `updated_at` — Timestamps

**PromptVersion**
- `id` — UUID
- `prompt_id` — Parent template ID (FK)
- `user_id` — Owner (denormalized for query efficiency)
- `version` — Auto-incrementing version number
- `content` — The actual prompt text
- `variables_json` — JSON array of variable names (e.g., `["user_query", "context"]`)
- `metadata_json` — Arbitrary metadata (author, notes, tags)
- `created_at` — When version was created

### API Endpoints

**Create template**
```
POST /api/prompts
Body: {"name": "research_prompt"}
Returns: PromptTemplate
```

**List templates**
```
GET /api/prompts
Returns: [PromptTemplate, ...]
```

**Get template with versions**
```
GET /api/prompts/{id}
Returns: PromptTemplate + versions: [PromptVersion, ...]
```

**Create new version**
```
POST /api/prompts/{id}/versions
Body: {
  "content": "You are a research assistant...",
  "variables": ["query", "sources"],
  "metadata": {"author": "alice", "purpose": "web search"}
}
Returns: PromptVersion
```

**Get specific version**
```
GET /api/prompts/{id}/versions/{version_number}
Returns: PromptVersion
```

**Diff two versions**
```
GET /api/prompts/{id}/diff?v1=1&v2=2
Returns: {"v1": 1, "v2": 2, "diff": "<unified diff>"}
```

### Storage Functions (`server/prompt_storage.py`)
- `create_prompt(user_id, name)` — Create template
- `list_prompts(user_id)` — List all user's templates
- `get_prompt(prompt_id, user_id)` — Get with ownership check
- `add_version(prompt_id, content, variables, metadata, user_id)` — Add version
- `get_version(prompt_id, version, user_id)` — Get specific version
- `list_versions(prompt_id, user_id)` — List all versions
- `diff_versions(prompt_id, v1, v2, user_id)` — Unified diff

### Dashboard Integration
- **Prompt Registry Page** — List templates, select to view versions
- **Version Viewer** — Display prompt content with metadata
- **Diff Viewer** — Side-by-side unified diff display
- **Edit Form** — Create new version with content, variables, metadata fields

## 3. LLM-as-Judge Evaluation

### Purpose
Assess agent outputs against defined criteria using an LLM judge, enabling quality measurement and feedback loops.

### Data Model

**EvalCriteria**
- `id` — UUID
- `user_id` — Owner
- `name` — Criteria name (e.g., "correctness")
- `description` — Human-readable description
- `rubric` — Detailed evaluation instructions for LLM
- `score_type` — "numeric" (1-5) or "binary" (pass/fail)
- `agent_name` — Target agent ("*" for all)
- `auto_eval` — Boolean; if true, evaluate all traces for this agent
- `enabled` — Boolean; if false, skip in evaluations
- `created_at`, `updated_at` — Timestamps

**EvalRun**
- `id` — UUID
- `criteria_id` — Which criteria was applied (FK)
- `trace_id` — Which trace was evaluated (FK)
- `user_id` — Owner
- `score` — 1-5 (numeric) or 0-1 (binary)
- `reasoning` — LLM's explanation of score
- `llm_provider` — Provider used (openai, anthropic, etc.)
- `llm_model` — Specific model used
- `prompt_name` — Optional prompt template used
- `prompt_version` — Optional prompt version number
- `created_at` — When evaluation ran

### API Endpoints

**Create criteria**
```
POST /api/eval/criteria
Body: {
  "name": "response_quality",
  "description": "Rate the quality of agent's response",
  "rubric": "Score 1-5: 1=nonsensical, 5=excellent and helpful",
  "score_type": "numeric",
  "agent_name": "*",
  "auto_eval": true,
  "enabled": true
}
Returns: EvalCriteria
```

**List criteria**
```
GET /api/eval/criteria
Returns: [EvalCriteria, ...]
```

**Update criteria**
```
PUT /api/eval/criteria/{id}
Body: {field updates}
Returns: EvalCriteria
```

**Delete criteria**
```
DELETE /api/eval/criteria/{id}
Returns: 204 No Content
```

**Run evaluation**
```
POST /api/eval/run
Body: {
  "criteria_id": "...",
  "trace_ids": ["trace1", "trace2"],
  "provider": "openai",  // optional: override user settings
  "model": "gpt-4"       // optional: override user settings
}
Returns: {"created_count": 2, "failed_count": 0}
```

**List evaluation runs**
```
GET /api/eval/runs?criteria_id=...&limit=50&offset=0
Returns: [EvalRun, ...]
```

**Get scores for trace**
```
GET /api/eval/scores?trace_id=...
Returns: [EvalRun, ...]  // all criteria evaluated for this trace
```

### Evaluation Flow (`server/eval_runner.py`)

1. **Build Judge Prompt**
   - Extract agent output from trace (root span or concatenated outputs)
   - Assemble criteria description + rubric
   - Include score instruction (numeric 1-5 vs binary 0-1)

2. **Call LLM**
   - Use user's configured provider + model
   - System prompt: "You are an evaluation judge..."
   - User prompt: Agent trace + criteria + rubric
   - JSON mode enabled for OpenAI (structured output)

3. **Parse Response**
   - Extract JSON: `{"score": <number>, "reasoning": "<string>"}`
   - Handle markdown code blocks if present
   - Clamp numeric scores to 1-5, binary to 0-1
   - Store in database

4. **Storage** (`server/eval_storage.py`)
   - `create_criteria(user_id, ...)` — Create evaluation criteria
   - `list_criteria(user_id, agent_name_filter)` — List criteria
   - `update_criteria(criteria_id, user_id, ...)` — Update
   - `delete_criteria(criteria_id, user_id)` — Delete
   - `create_eval_run(criteria_id, trace_id, score, reasoning, ...)` — Record result
   - `list_eval_runs(criteria_id, limit, offset)` — Query results
   - `get_eval_scores(trace_id, user_id)` — Get all scores for a trace

### Auto-Evaluation

When `auto_eval=true` on a criteria:
- After trace completion, evaluate all traces matching `agent_name`
- Call `run_eval()` with user's LLM settings
- Store results in `EvalRun` table
- Dashboard updates in real-time (Recharts score visualization)

### Dashboard Integration
- **Eval Dashboard Page** — View and manage criteria
- **Criteria Management** — Create, edit, delete with form UI
- **Score Visualization** — Charts showing score distribution over time
- **Trace Detail** — Show all eval scores for selected trace
- **Evaluation History** — List runs with filtering by criteria, date range

## SDK Integration

### Python SDK — Span Processors

The SDK now supports `SpanProcessor` protocol for lifecycle hooks:

```python
from agentlens import Tracer, SpanProcessor

class MyProcessor(SpanProcessor):
    def on_start(self, span):
        print(f"Span {span.name} started")

    def on_end(self, span):
        print(f"Span {span.name} ended with output: {span.output[:100]}")

tracer = Tracer()
tracer.configure(server_url="http://localhost:3000")
tracer.add_processor(MyProcessor())

@tracer.trace(name="MyAgent")
def my_agent():
    with tracer.span("search", "tool_call") as s:
        result = search("query")
        s.set_output(result)
    return result
```

**Use Cases:**
- Custom logging/metrics collection
- Span modification before export
- Performance monitoring
- Integration with observability platforms

## Testing

**Plugin Tests** (`server/tests/test_plugin_loader.py`)
- Plugin loading from directory
- Hook invocation (on_trace_created, on_trace_completed)
- Error handling (plugin exceptions don't crash server)
- Route registration

**Prompt Tests** (`server/tests/test_prompt.py`)
- CRUD operations for templates and versions
- Version auto-increment
- Diff generation (unified format)
- User isolation (cross-user access denied)

**Evaluation Tests** (`server/tests/test_eval.py`)
- Criteria CRUD
- Judge prompt building
- LLM response parsing (JSON extraction, score clamping)
- Evaluation runs with numeric and binary scores
- Auto-eval trigger on trace completion

## Backward Compatibility

- **No Breaking Changes** — All Phase 2 features are additive
- Existing traces, spans, alerts, autopsies unchanged
- Plugin system is optional (no plugins = no plugins loaded)
- Prompt and eval systems are independent of other features
- SDK SpanProcessor is optional; existing code works without it

## Performance Considerations

- **Plugin Hooks** — Fire-and-forget; exceptions logged, never block trace ingestion
- **Evaluation** — Asynchronous; LLM calls happen in background (future: async queue)
- **Prompt Storage** — Indexed on (user_id, name) for fast lookups
- **Eval Results** — Indexed on (criteria_id, trace_id), (user_id, created_at)
