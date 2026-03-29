# AgentLens .NET SDK

Debug AI agents visually — .NET SDK for [AgentLens](https://github.com/agentlens/agentlens).

## Installation

```bash
dotnet add package AgentLens.Observe
```

## Quick start

```csharp
using AgentLens;

// Configure once at startup
AgentLensClient.Configure("http://localhost:8000");

// Wrap an agent run in a trace
using (AgentLensClient.Trace("my-agent"))
{
    // Create child spans for discrete steps
    using (var span = AgentLensClient.Span("search", "tool_call"))
    {
        var results = await SearchAsync(query);
        span.SetOutput(results.ToString())
            .SetCost("gpt-4o", inputTokens: 120, outputTokens: 60)
            .SetMetadata("result_count", results.Count)
            .Log("search complete");
    }

    using (var span = AgentLensClient.Span("summarise", "llm_call"))
    {
        var summary = await SummariseAsync(results);
        span.SetOutput(summary);
    }
}
```

## Streaming mode

Send spans to the dashboard as they complete (enables live topology view):

```csharp
AgentLensClient.Configure("http://localhost:8000", streaming: true);
```

## Span fluent API

| Method | Description |
|---|---|
| `SetOutput(string)` | Record the span's output (truncated to 4 096 chars) |
| `SetCost(model, inputTokens, outputTokens)` | Record token cost — USD calculated automatically |
| `SetMetadata(key, value)` | Attach arbitrary key/value metadata |
| `Log(message, extra?)` | Append a timestamped log entry to the span |

## Exporters and processors

```csharp
// ISpanExporter — receives every completed span
AgentLensClient.AddExporter(new MyOtelExporter());

// ISpanProcessor — on_start / on_end lifecycle hooks
AgentLensClient.AddProcessor(new MyAuditProcessor());
```

## Context

```csharp
var trace = AgentLensClient.CurrentTrace; // null if outside a trace
```

## Semantic Kernel integration

```csharp
using AgentLens.Integrations;

SemanticKernelIntegration.Patch(); // placeholder — full wiring coming soon
```

## Supported models (cost calculation)

The SDK ships a pricing table for OpenAI (GPT-4o, GPT-4.1, o1/o3), Anthropic
(Claude 3.5, Claude 4), Google (Gemini 1.5, 2.0), DeepSeek, and Meta Llama
families. Provider prefixes (`openai/gpt-4o`) and version suffixes
(`gpt-4o-2024-05-13`) are resolved automatically.

## Build

```bash
cd sdk-dotnet
dotnet build
dotnet test
```

## Requirements

- .NET 8 LTS or later
- No external NuGet dependencies (uses only `System.Net.Http` and `System.Text.Json`)
