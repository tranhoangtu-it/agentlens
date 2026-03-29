using Xunit;

namespace AgentLens.Tests;

public sealed class TracerTests
{
    // -------------------------------------------------------------------------
    // TraceScope
    // -------------------------------------------------------------------------

    [Fact]
    public void Trace_SetsCurrentTrace_InsideScope()
    {
        using (AgentLensClient.Trace("test-agent"))
        {
            Assert.NotNull(AgentLensClient.CurrentTrace);
            Assert.Equal("test-agent", AgentLensClient.CurrentTrace!.AgentName);
        }
    }

    [Fact]
    public void Trace_ClearsCurrentTrace_AfterDispose()
    {
        using (AgentLensClient.Trace("test-agent")) { }
        Assert.Null(AgentLensClient.CurrentTrace);
    }

    [Fact]
    public void Trace_RootSpan_RecordedInTrace()
    {
        ActiveTrace? captured = null;
        using (AgentLensClient.Trace("root-test"))
        {
            captured = AgentLensClient.CurrentTrace;
        }
        Assert.NotNull(captured);
        Assert.Single(captured!.Spans);
        Assert.Equal("root-test", captured.Spans[0].Name);
        Assert.Equal("agent_run", captured.Spans[0].Type);
    }

    [Fact]
    public void Trace_RootSpan_HasEndMs_AfterDispose()
    {
        ActiveTrace? captured = null;
        using (AgentLensClient.Trace("timing-test"))
        {
            captured = AgentLensClient.CurrentTrace;
        }
        Assert.NotNull(captured!.Spans[0].EndMs);
        Assert.True(captured.Spans[0].EndMs >= captured.Spans[0].StartMs);
    }

    // -------------------------------------------------------------------------
    // SpanContext
    // -------------------------------------------------------------------------

    [Fact]
    public void Span_InsideTrace_CreatesChildSpan()
    {
        ActiveTrace? captured = null;
        using (AgentLensClient.Trace("parent"))
        {
            captured = AgentLensClient.CurrentTrace;
            using (AgentLensClient.Span("child", "tool_call")) { }
        }
        Assert.Equal(2, captured!.Spans.Count);
        var child = captured.Spans[1];
        Assert.Equal("child", child.Name);
        Assert.Equal("tool_call", child.Type);
        Assert.NotNull(child.ParentId);
        Assert.Equal(captured.Spans[0].SpanId, child.ParentId);
    }

    [Fact]
    public void Span_OutsideTrace_ReturnsNoop_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
        {
            using var span = AgentLensClient.Span("orphan");
            span.SetOutput("x").SetMetadata("k", "v").Log("msg");
        });
        Assert.Null(ex);
    }

    [Fact]
    public void Span_SetOutput_TruncatesAt4096()
    {
        SpanData? captured = null;

        using (AgentLensClient.Trace("trunc-test"))
        {
            var active = AgentLensClient.CurrentTrace!;
            using (var ctx = AgentLensClient.Span("s"))
            {
                ctx.SetOutput(new string('x', 5000));
                // Span was pushed on construction — index 1 in the list
                captured = active.Spans.Count > 1 ? active.Spans[1] : null;
            }
        }

        Assert.NotNull(captured);
        Assert.Equal(4096, captured!.Output?.Length);
    }

    [Fact]
    public void Span_SetCost_PopulatesSpanCost()
    {
        SpanData? captured = null;

        using (AgentLensClient.Trace("cost-test"))
        {
            var active = AgentLensClient.CurrentTrace!;
            using (var ctx = AgentLensClient.Span("llm", "llm_call"))
            {
                ctx.SetCost("gpt-4o", inputTokens: 100, outputTokens: 50);
                captured = active.Spans.Count > 1 ? active.Spans[1] : null;
            }
        }

        Assert.NotNull(captured);
        Assert.NotNull(captured!.Cost);
        Assert.Equal("gpt-4o", captured.Cost!.Model);
        Assert.Equal(100, captured.Cost.InputTokens);
        Assert.Equal(50, captured.Cost.OutputTokens);
        Assert.NotNull(captured.Cost.Usd);
    }

    [Fact]
    public void Span_SetMetadata_StoresKeyValue()
    {
        SpanData? captured = null;

        using (AgentLensClient.Trace("meta-test"))
        {
            var active = AgentLensClient.CurrentTrace!;
            using (var ctx = AgentLensClient.Span("step"))
            {
                ctx.SetMetadata("result_count", 42);
                captured = active.Spans.Count > 1 ? active.Spans[1] : null;
            }
        }

        Assert.NotNull(captured);
        Assert.True(captured!.Metadata.ContainsKey("result_count"));
        Assert.Equal(42, captured.Metadata["result_count"]);
    }

    [Fact]
    public void Span_Log_AddsLogEntry()
    {
        SpanData? captured = null;

        using (AgentLensClient.Trace("log-test"))
        {
            var active = AgentLensClient.CurrentTrace!;
            using (var ctx = AgentLensClient.Span("step"))
            {
                ctx.Log("hello world");
                captured = active.Spans.Count > 1 ? active.Spans[1] : null;
            }
        }

        Assert.NotNull(captured);
        Assert.True(captured!.Metadata.ContainsKey("logs"));
        var logs = captured.Metadata["logs"] as List<object?>;
        Assert.NotNull(logs);
        Assert.Single(logs!);
        var entry = logs![0] as Dictionary<string, object?>;
        Assert.NotNull(entry);
        Assert.Equal("hello world", entry!["message"]);
    }

    [Fact]
    public void Span_Log_TruncatesMessageAt1024()
    {
        SpanData? captured = null;

        using (AgentLensClient.Trace("log-trunc-test"))
        {
            var active = AgentLensClient.CurrentTrace!;
            using (var ctx = AgentLensClient.Span("step"))
            {
                ctx.Log(new string('a', 2000));
                captured = active.Spans.Count > 1 ? active.Spans[1] : null;
            }
        }

        var logs = captured!.Metadata["logs"] as List<object?>;
        var entry = logs![0] as Dictionary<string, object?>;
        Assert.Equal(1024, ((string)entry!["message"]!).Length);
    }

    [Fact]
    public void Span_HasEndMs_AfterDispose()
    {
        SpanData? captured = null;

        using (AgentLensClient.Trace("endms-test"))
        {
            var active = AgentLensClient.CurrentTrace!;
            using (AgentLensClient.Span("timed"))
            {
                captured = active.Spans.Count > 1 ? active.Spans[1] : null;
            }
        }

        Assert.NotNull(captured);
        Assert.NotNull(captured!.EndMs);
        Assert.True(captured.EndMs >= captured.StartMs);
    }

    // -------------------------------------------------------------------------
    // AgentLensClient.Log (static convenience method)
    // -------------------------------------------------------------------------

    [Fact]
    public void Log_OutsideTrace_DoesNotThrow()
    {
        var ex = Record.Exception(() => AgentLensClient.Log("orphan log"));
        Assert.Null(ex);
    }

    [Fact]
    public void Log_InsideTrace_AddsEntryToCurrentSpan()
    {
        ActiveTrace? captured = null;

        using (AgentLensClient.Trace("static-log-test"))
        {
            captured = AgentLensClient.CurrentTrace;
            AgentLensClient.Log("static message");
        }

        Assert.NotNull(captured);
        var rootSpan = captured!.Spans[0];
        var logs = rootSpan.Metadata["logs"] as List<object?>;
        Assert.NotNull(logs);
        Assert.Single(logs!);
    }

    // -------------------------------------------------------------------------
    // Processor hooks
    // -------------------------------------------------------------------------

    [Fact]
    public void AddProcessor_ReceivesOnStart_AndOnEnd()
    {
        var processor = new RecordingProcessor();
        AgentLensClient.AddProcessor(processor);

        using (AgentLensClient.Trace("proc-test"))
        {
            using (AgentLensClient.Span("child")) { }
        }

        Assert.Contains(processor.StartedNames, n => n == "proc-test");
        Assert.Contains(processor.EndedNames, n => n == "proc-test");
        Assert.Contains(processor.StartedNames, n => n == "child");
        Assert.Contains(processor.EndedNames, n => n == "child");
    }

    // -------------------------------------------------------------------------
    // Exporter hooks
    // -------------------------------------------------------------------------

    [Fact]
    public void AddExporter_ReceivesCompletedSpans()
    {
        var exporter = new RecordingExporter();
        AgentLensClient.AddExporter(exporter);

        using (AgentLensClient.Trace("export-test"))
        {
            using (AgentLensClient.Span("export-child")) { }
        }

        Assert.Contains(exporter.ExportedNames, n => n == "export-test");
        Assert.Contains(exporter.ExportedNames, n => n == "export-child");
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private sealed class RecordingProcessor : ISpanProcessor
    {
        public List<string> StartedNames { get; } = new();
        public List<string> EndedNames { get; } = new();
        public void OnStart(SpanData span) => StartedNames.Add(span.Name);
        public void OnEnd(SpanData span) => EndedNames.Add(span.Name);
    }

    private sealed class RecordingExporter : ISpanExporter
    {
        public List<string> ExportedNames { get; } = new();
        public void ExportSpan(SpanData span) => ExportedNames.Add(span.Name);
        public void Shutdown() { }
    }
}
