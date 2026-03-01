---
title: TypeScript SDK
description: Full API reference for the AgentLens TypeScript/Node.js SDK
---

## Installation

```bash
npm install agentlens-observe
```

Requires Node.js 18+. Zero production dependencies.

## Configuration

```typescript
import * as agentlens from "agentlens-observe";

agentlens.configure({
  serverUrl: "http://localhost:3000",
  apiKey: "al_your_api_key",   // optional — from dashboard Settings → API Keys
  batchSize: 1,                 // flush every N spans (default: 1 = immediate)
  batchInterval: 0,             // flush every N ms (default: 0 = disabled)
});
```

## `agentlens.trace()`

Higher-order function that wraps an async callback as a top-level agent trace.

```typescript
const result = await agentlens.trace("ResearchAgent", async () => {
  // spans created inside here are children of this trace
  return "done";
});
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | Display name for the trace |
| `fn` | `() => Promise<T>` | Async function to trace |

Returns `Promise<T>` — the return value of `fn`.

## `agentlens.span()`

Creates a child span within the current trace. Uses `enter()` / `exit()` pattern.

```typescript
const s = agentlens.span("web_search", "tool_call").enter();
const data = await search(query);
s.setOutput(data);
s.setCost("gpt-4o", { inputTokens: 500, outputTokens: 200 });
s.exit();
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | Span name |
| `kind` | `string` | One of `tool_call`, `llm_call`, `agent_run`, `task` |

### Span Methods

| Method | Description |
|--------|-------------|
| `s.enter()` | Start the span, returns `this` for chaining |
| `s.exit()` | End the span and flush |
| `s.setOutput(value)` | Record the span's output (any JSON-serializable value) |
| `s.setInput(value)` | Record the span's input |
| `s.setCost(model, { inputTokens, outputTokens })` | Track LLM cost |
| `s.setError(error)` | Mark span as failed |
| `s.setMetadata(key, value)` | Attach arbitrary metadata |

## `agentlens.log()`

Attach a log entry to the current active span.

```typescript
await agentlens.trace("MyAgent", async () => {
  agentlens.log("Starting research phase", { phase: "research", step: 1 });
  // logs appear in span.metadata.logs
});
```

## `agentlens.currentTrace()`

Get the current trace ID (useful for correlating with external systems).

```typescript
const traceId = agentlens.currentTrace();
console.log("Trace ID:", traceId);
```

## `agentlens.addExporter()`

Register a custom span exporter.

```typescript
agentlens.addExporter({
  export(span) {
    myMonitoring.record(span);
  }
});
```

## Full Example

```typescript
import * as agentlens from "agentlens-observe";

agentlens.configure({ serverUrl: "http://localhost:3000" });

async function runResearch(query: string): Promise<string> {
  return agentlens.trace("ResearchAgent", async () => {
    agentlens.log("Starting research", { query });

    const searchSpan = agentlens.span("web_search", "tool_call").enter();
    searchSpan.setInput({ query });
    const results = await searchWeb(query);
    searchSpan.setOutput(results.slice(0, 3));
    searchSpan.exit();

    const llmSpan = agentlens.span("summarize", "llm_call").enter();
    llmSpan.setInput({ text: results });
    const summary = await llmSummarize(results);
    llmSpan.setOutput(summary);
    llmSpan.setCost("gpt-4o", { inputTokens: 800, outputTokens: 300 });
    llmSpan.exit();

    return summary;
  });
}

runResearch("Latest breakthroughs in AI reasoning");
```

## ESM / CJS

The package ships dual ESM + CJS outputs. Both are supported automatically by Node.js module resolution.
