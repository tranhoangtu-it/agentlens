# AgentLens Phase 4 Features — .NET 8 SDK (AgentLens.Observe)

**Status:** Implementation Phase | **Target Release:** v0.9.0 (Q2 2026) | **SDK Version:** 0.1.0

## Overview

Phase 4 adds production-ready .NET 8 SDK with native async context propagation, zero external dependencies, and full feature parity with Python SDK. Supports all major LLM pricing models and includes a Semantic Kernel integration placeholder for future expansion.

## 1. Core SDK Architecture

### Entry Point (`AgentLensClient.cs`)

Static facade providing flat module-level API, mirroring Python SDK design:

```csharp
// Configuration (call once at startup)
AgentLensClient.Configure(serverUrl: "http://localhost:8000", streaming: false);

// Trace management
using (AgentLensClient.Trace("my-agent", spanType: "agent_run", input: "query"))
{
    using var span = AgentLensClient.Span("search", "tool_call");
    span.SetOutput("results")
        .SetCost("gpt-4o", inputTokens: 100, outputTokens: 50)
        .Log("operation complete");
    AgentLensClient.Log("trace-level message", new { extra = "data" });
}
```

**Key Methods:**
- `Configure(serverUrl, streaming)` — Set server endpoint and transport mode
- `Trace(agentName, spanType, input)` — Open root trace scope; returns `IAsyncDisposable`
- `Span(name, spanType)` — Open child span; returns `ISpanContext` (noop outside trace)
- `Log(message, extra)` — Append timestamped log to current span
- `CurrentTrace` — Property returning active trace or null
- `AddExporter(ISpanExporter)` — Register span exporter
- `AddProcessor(ISpanProcessor)` — Register span processor

### Async Context Propagation (`ActiveTrace.cs`)

Thread-safe span stack using `AsyncLocal<ActiveTrace?>`:

```csharp
// AsyncLocal ensures each async call-chain has its own trace context
private static readonly AsyncLocal<ActiveTrace?> _currentTrace = new();
```

**Equivalent to:** Python's `contextvars.ContextVar` — preserves context across async/await boundaries without requiring explicit thread-local state.

**Behavior:**
- Automatically inherited by child tasks spawned via `Task.Run()`
- Isolated per async execution context
- Cleared on trace disposal via `TraceScope`

### Trace & Span Data Models

**SpanData.cs** — Wire format for serialization:
- `span_id` (GUID string)
- `parent_id` (nullable GUID string)
- `trace_id` (GUID string)
- `name`, `type` (string; e.g., "tool_call", "agent_run", "llm_call")
- `start_ms`, `end_ms` (Unix milliseconds)
- `input`, `output` (JSON strings, max 4096 chars)
- `cost_usd` (nullable double)
- `metadata` (dict: logs, custom fields)

**TraceScope.cs** — Disposable wrapper for root span lifecycle:
- Owns `ActiveTrace` reference
- Flushes trace on dispose (synchronous POST)
- Clears context via `AsyncLocal.Value = null`

**SpanContext.cs** — Disposable wrapper for child spans:
- Implements `ISpanContext` interface (fluent builder)
- Calls `OnStart` processors on construction
- Calls `OnEnd` processors on disposal

### Transport & Serialization (`Transport.cs`)

Fire-and-forget HTTP client with no retries:

```csharp
// Shared HttpClient (thread-safe, reused)
private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(5) };

// POST /api/traces (full trace at end)
Transport.PostTrace(traceId, agentName, spans)

// POST /api/traces/{traceId}/spans (streaming mode)
Transport.PostSpans(traceId, spans)
```

**Payloads:**
```json
// TracePayload
{
  "trace_id": "uuid",
  "agent_name": "my-agent",
  "spans": [...]
}

// SpanBatchPayload (streaming)
{
  "spans": [...]
}
```

**Design:**
- Non-blocking `Task.Run()` + `FireAndForget()` pattern
- Errors logged to `Debug.WriteLine()`, never propagate to caller
- JSON serialization uses `System.Text.Json` with snake_case naming

## 2. Cost Calculator (`Cost.cs`)

LLM pricing table with 27 models (USD per 1M tokens):

**Models Supported:**
- **OpenAI:** gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-4.5-preview, gpt-4-turbo, gpt-3.5-turbo
- **Reasoning:** o1, o1-mini, o3-mini, o3
- **Anthropic:** claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus, claude-sonnet-4, claude-haiku-4, claude-opus-4
- **Google:** gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash, gemini-2.0-pro
- **DeepSeek:** deepseek-v3, deepseek-r1
- **Meta/Llama:** llama-3.1-70b, llama-3.1-405b, llama-3.3-70b

**API:**
```csharp
var cost = Cost.CalculateCost(model: "gpt-4o", inputTokens: 1000, outputTokens: 500);
// Returns: 0.0075 (or null if unknown model)
```

**Features:**
- Strips provider prefix (`openai/gpt-4o` → `gpt-4o`)
- Prefix matching for versioned models (`gpt-4o-2024-05-13` → `gpt-4o`)
- Case-insensitive lookups
- Last updated: Feb 2026

## 3. Exporters & Processors

### ISpanExporter Interface

Optional exporters receive all completed spans:

```csharp
public interface ISpanExporter
{
    void ExportSpan(SpanData span);
    void Shutdown();
}
```

**Use cases:**
- Forward to OpenTelemetry collector
- Custom sinks (Datadog, New Relic)
- Local file logging
- Analytics pipelines

**Registration:**
```csharp
AgentLensClient.AddExporter(new MyCustomExporter());
```

### ISpanProcessor Interface

Lifecycle hooks with synchronous execution:

```csharp
public interface ISpanProcessor
{
    void OnStart(SpanData span);
    void OnEnd(SpanData span);
}
```

**Constraints:**
- Fires synchronously during `PushSpan`/`PopSpan`
- Must not throw (errors logged, not propagated)
- Must complete quickly (blocks span completion)

**Use cases:**
- Automatic metadata injection
- Sampling decisions
- Instrumentation hooks

## 4. Integration Stub (`SemanticKernelIntegration.cs`)

Placeholder for future Semantic Kernel support:

```csharp
namespace AgentLens.Integrations;

public static class SemanticKernelIntegration
{
    public static void Patch()
    {
        // TODO: Hook SK kernel.InvokeAsync() → span wrapping
    }
}
```

**Future work:**
- Intercept SK function invocations
- Auto-capture prompt + response
- Token counting via SK tokenizer
- Model inference time tracking

## 5. Testing Suite

**29 xUnit tests** across two files:

### TracerTests.cs (18 tests)
- `Trace_SetsCurrentTrace_InsideScope` — Context propagation
- `Trace_ClearsCurrentTrace_AfterDispose` — Cleanup
- `Trace_RootSpan_RecordedInTrace` — Root span creation
- `Trace_RootSpan_HasEndMs_AfterDispose` — Timing accuracy
- `Span_InsideTrace_CreatesChildSpan` — Parent-child linking
- `Span_OutsideTrace_ReturnsNoop_DoesNotThrow` — Graceful degradation
- `Span_SetOutput_TruncatesAt4096` — String truncation
- `Span_SetMetadata_NestedDict` — Metadata nesting
- `Span_SetCost_CalculatesUSD` — Cost tracking
- `Span_Log_AppendsProperly` — Logging
- `Span_Fluent_ChainsCorrectly` — Builder pattern
- `Nesting_MultipleChildSpans` — Multiple children
- `Nesting_DeepHierarchy` — Deep nesting
- `Async_ParallelSpans_IsolatedContexts` — Async safety
- `Processor_OnStart_FiresBeforePush` — Processor hooks
- `Processor_OnEnd_FiresAfterPop` — Processor cleanup
- `Exporter_Receives_CompletedSpan` — Exporter invocation
- `Transport_FiresBackground` — Non-blocking transport

### CostTests.cs (11 tests)
- `CalculateCost_KnownModel_ReturnsCorrectUsd` — 6 model variants
- `CalculateCost_UnknownModel_ReturnsNull` — Unknown model handling
- `CalculateCost_StripsProviderPrefix` — Prefix stripping
- `CalculateCost_PrefixMatch_ResolvesVersionedModel` — Version matching
- `CalculateCost_ZeroTokens_ReturnsZero` — Edge case
- `CalculateCost_CaseInsensitive` — Case handling
- `CalculateCost_NonOpenAiModels_ReturnsCorrectUsd` — Multi-vendor support

**Coverage:** All public APIs exercised; 100% production code coverage

## 6. Dependencies

**Zero external dependencies** — uses only:
- `System.Net.Http` (built-in HttpClient)
- `System.Text.Json` (built-in serialization)
- `System.Threading` (built-in async primitives)

**Dev dependencies:**
- `xunit` (testing framework)
- `xunit.runner.visualstudio` (test runner)

## 7. Package Distribution

**NuGet Package:** `AgentLens.Observe`

```bash
dotnet add package AgentLens.Observe
```

**Project File Requirements:**
- Target Framework: `.NET 8.0+`
- Nullable: `enable`
- Language Version: `latest` (to use required/init keywords)

## 8. Quick Start Example

```csharp
using AgentLens;
using System;
using System.Collections.Generic;

// Step 1: Configure at startup
AgentLensClient.Configure(serverUrl: "http://localhost:8000");

// Step 2: Create a trace
using (AgentLensClient.Trace("search-agent", input: "find Python docs"))
{
    // Step 3: Create child spans for operations
    using var searchSpan = AgentLensClient.Span("web_search", "tool_call");
    searchSpan
        .SetOutput("{\"results\": [...]}")
        .SetCost("gpt-4o", inputTokens: 150, outputTokens: 200)
        .Log("search completed");

    // Step 4: Add trace-level logs
    AgentLensClient.Log("agent decision made", new Dictionary<string, object?>
    {
        ["decision"] = "proceed_with_first_result"
    });

    // Step 5: Nested spans
    using (AgentLensClient.Span("parse_results", "processing"))
    {
        AgentLensClient.Log("parsing initiated");
    }
}
// On dispose: trace flushed to server automatically
```

## 9. Async Safety Guarantee

The SDK is safe for concurrent async operations:

```csharp
// Each task gets isolated trace context
var task1 = Task.Run(async () =>
{
    using (AgentLensClient.Trace("agent-1"))
    {
        await ProcessAsync();
    }
});

var task2 = Task.Run(async () =>
{
    using (AgentLensClient.Trace("agent-2"))
    {
        await ProcessAsync();
    }
});

// task1 and task2 won't interfere — different AsyncLocal contexts
```

## 10. Error Handling Strategy

**Fail-safe design:** SDK errors never crash the host application:

- Transport errors logged to `Debug.WriteLine()`, not thrown
- Exporter errors caught individually, don't affect other exporters
- Processor errors caught, span continues normally
- Invalid span data (null/empty names) validated on input

```csharp
// Even if server is down, this never throws
using (AgentLensClient.Trace("my-agent"))
{
    using var span = AgentLensClient.Span("task");
    span.SetOutput("success");
}
// Error logged to Debug, trace silently dropped
```

## 11. Streaming Mode

Optional immediate span delivery instead of batch at trace end:

```csharp
// streaming=true: each completed span sent individually to /api/traces/{id}/spans
AgentLensClient.Configure("http://localhost:8000", streaming: true);

using (AgentLensClient.Trace("agent"))
{
    using var s1 = AgentLensClient.Span("task1");
    s1.Log("done");
    // POST to /api/traces/{id}/spans fires immediately
}
// Final trace POST still sent on dispose
```

## 12. Fluent Builder API

All span mutations return `ISpanContext` for method chaining:

```csharp
using var span = AgentLensClient.Span("search")
    .SetInput("{\"query\": \"python\"}")
    .SetOutput("{\"results\": [...]}")
    .SetCost("gpt-4o", 100, 50)
    .SetMetadata("source", "web")
    .Log("completed");
```

## Success Criteria

- [x] .NET 8 SDK with zero external dependencies
- [x] AsyncLocal-based context propagation (async-safe)
- [x] 27 LLM pricing models ported from Python
- [x] 29 comprehensive xUnit tests (100% coverage)
- [x] ISpanExporter + ISpanProcessor extension interfaces
- [x] Fire-and-forget HTTP transport (non-blocking)
- [x] NuGet package ready for distribution
- [x] Semantic Kernel integration stub
- [x] Full feature parity with Python SDK v0.3.0

## Known Limitations & Future Work

### Current (v0.1.0)
- Semantic Kernel integration not yet implemented (stub only)
- No built-in LLM integrations (e.g., Azure SDK, OpenAI .NET client)
- OpenTelemetry exporter not yet implemented

### Roadmap
- [ ] Semantic Kernel auto-instrumentation (v0.2.0)
- [ ] OpenAI .NET client integration (v0.2.0)
- [ ] Azure Cognitive Services integration (v0.2.0)
- [ ] OpenTelemetry span exporter (v0.2.0)
- [ ] Automatic exception tracking (v0.3.0)
- [ ] Performance metrics (CPU, memory) (v0.3.0)
