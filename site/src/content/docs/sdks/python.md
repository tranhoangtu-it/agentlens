---
title: Python SDK
description: Full API reference for the AgentLens Python SDK
---

## Installation

```bash
pip install agentlens-observe
```

Requires Python 3.10+.

## Configuration

```python
import agentlens

agentlens.configure(
    server_url="http://localhost:3000",
    api_key="al_your_api_key",   # optional — from dashboard Settings → API Keys
    batch_size=1,                 # flush every N spans (default: 1 = immediate)
    batch_interval=0.0,           # flush every N seconds (default: 0 = disabled)
)
```

## `@agentlens.trace`

Decorator that wraps a function as a top-level agent trace.

```python
@agentlens.trace(name="ResearchAgent")
def run_agent(query: str) -> str:
    ...

# Async support
@agentlens.trace(name="AsyncAgent")
async def run_async_agent(query: str) -> str:
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Display name for the trace in the dashboard |

## `agentlens.span()`

Context manager that creates a child span within the current trace.

```python
with agentlens.span("web_search", "tool_call") as s:
    result = search(query)
    s.set_output(result)
    s.set_cost("gpt-4o", input_tokens=500, output_tokens=200)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Span name |
| `kind` | `str` | One of `tool_call`, `llm_call`, `agent_run`, `task` |

### Span Methods

| Method | Description |
|--------|-------------|
| `s.set_output(value)` | Record the span's output (any JSON-serializable value) |
| `s.set_input(value)` | Record the span's input |
| `s.set_cost(model, input_tokens, output_tokens)` | Track LLM cost |
| `s.set_error(error)` | Mark span as failed with error message |
| `s.set_metadata(**kwargs)` | Attach arbitrary key-value metadata |

### Supported Models for Cost Tracking

GPT-4.1, GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet, Claude 3 Opus, Gemini 2.0 Flash, Gemini 1.5 Pro, DeepSeek-V3, Llama 3.3 70B, and 18 more.

## `agentlens.log()`

Attach a log entry to the current active span.

```python
@agentlens.trace(name="MyAgent")
def run():
    agentlens.log("Starting research phase", phase="research", step=1)
    # logs appear in span.metadata["logs"]
```

## `agentlens.add_exporter()`

Bridge spans to an external backend.

```python
from agentlens.exporters.otel import AgentLensOTelExporter

agentlens.add_exporter(AgentLensOTelExporter())
```

## Batch Transport

For high-throughput agents, batch spans to reduce HTTP overhead:

```python
agentlens.configure(
    server_url="http://localhost:3000",
    batch_size=50,       # flush every 50 spans
    batch_interval=5.0,  # or every 5 seconds, whichever comes first
)
```

## Full Example

```python
import agentlens

agentlens.configure(server_url="http://localhost:3000")

@agentlens.trace(name="ResearchAgent")
def run_research(query: str) -> str:
    agentlens.log("Starting research", query=query)

    with agentlens.span("web_search", "tool_call") as s:
        s.set_input({"query": query})
        results = search_web(query)
        s.set_output(results[:3])

    with agentlens.span("summarize", "llm_call") as s:
        s.set_input({"text": results})
        summary = llm_summarize(results)
        s.set_output(summary)
        s.set_cost("gpt-4o", input_tokens=800, output_tokens=300)

    return summary

run_research("Latest breakthroughs in AI reasoning")
```
