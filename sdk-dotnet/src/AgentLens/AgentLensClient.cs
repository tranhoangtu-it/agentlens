namespace AgentLens;

/// <summary>
/// Main static entry point for the AgentLens .NET SDK.
/// Mirrors the flat module-level API of the Python SDK (__init__.py).
///
/// Quick start:
///   AgentLensClient.Configure("http://localhost:8000");
///   using (AgentLensClient.Trace("my-agent"))
///   {
///       using var span = AgentLensClient.Span("search", "tool_call");
///       span.SetOutput("results").Log("done");
///   }
/// </summary>
public static class AgentLensClient
{
    // AsyncLocal gives each async call-chain its own trace context,
    // equivalent to Python's contextvars.ContextVar.
    private static readonly AsyncLocal<ActiveTrace?> _currentTrace = new();

    private static readonly List<ISpanExporter> _exporters = new();
    private static readonly List<ISpanProcessor> _processors = new();
    private static readonly object _registryLock = new();
    private static bool _streamingDefault;

    // -------------------------------------------------------------------------
    // Configuration
    // -------------------------------------------------------------------------

    /// <summary>
    /// Configure the server URL and transport options.
    /// Call once at application startup before any traces are created.
    /// </summary>
    /// <param name="serverUrl">Base URL of the AgentLens server.</param>
    /// <param name="streaming">
    /// When true, completed spans are sent immediately as they finish rather
    /// than waiting for the full trace to complete.
    /// </param>
    public static void Configure(string serverUrl, bool streaming = false)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(serverUrl);
        Transport.SetServerUrl(serverUrl);
        _streamingDefault = streaming;
    }

    /// <summary>Register an exporter to receive every completed span.</summary>
    public static void AddExporter(ISpanExporter exporter)
    {
        ArgumentNullException.ThrowIfNull(exporter);
        lock (_registryLock) { _exporters.Add(exporter); }
    }

    /// <summary>Register a processor for span lifecycle hooks (OnStart / OnEnd).</summary>
    public static void AddProcessor(ISpanProcessor processor)
    {
        ArgumentNullException.ThrowIfNull(processor);
        lock (_registryLock) { _processors.Add(processor); }
    }

    // -------------------------------------------------------------------------
    // Trace context
    // -------------------------------------------------------------------------

    /// <summary>
    /// Returns the active trace for the current async context, or null when
    /// called outside a trace boundary.
    /// </summary>
    public static ActiveTrace? CurrentTrace => _currentTrace.Value;

    // -------------------------------------------------------------------------
    // Tracing — using-statement API
    // -------------------------------------------------------------------------

    /// <summary>
    /// Opens a new root-level trace context. Dispose to close the trace and
    /// flush all spans to the server.
    ///
    ///   using (AgentLensClient.Trace("my-agent")) { ... }
    /// </summary>
    /// <param name="agentName">Human-readable name for this agent run.</param>
    /// <param name="spanType">Root span type tag (default: "agent_run").</param>
    /// <param name="input">Optional input string recorded on the root span.</param>
    public static TraceScope Trace(
        string agentName,
        string spanType = "agent_run",
        string? input = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(agentName);

        var active = new ActiveTrace(
            traceId:   Guid.NewGuid().ToString(),
            agentName: agentName,
            streaming: _streamingDefault);

        var root = new SpanData(
            spanId:   Guid.NewGuid().ToString(),
            parentId: null,
            name:     agentName,
            type:     spanType,
            startMs:  NowMs())
        {
            Input = Truncate(input, 4096)
        };

        // Set context before pushing span so processors can read CurrentTrace
        _currentTrace.Value = active;
        active.PushSpan(root);

        return new TraceScope(active, root, _currentTrace);
    }

    /// <summary>
    /// Opens a child span within the current trace. Returns a no-op context
    /// when called outside a trace — never throws.
    ///
    ///   using var span = AgentLensClient.Span("search", "tool_call");
    /// </summary>
    public static ISpanContext Span(string name, string spanType = "tool_call")
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);

        var active = _currentTrace.Value;
        if (active is null)
            return NoopSpanContext.Instance;

        var span = new SpanData(
            spanId:   Guid.NewGuid().ToString(),
            parentId: active.CurrentSpanId(),
            name:     name,
            type:     spanType,
            startMs:  NowMs());

        return new SpanContext(active, span);
    }

    /// <summary>
    /// Appends a timestamped log entry to the innermost active span.
    /// No-ops silently when called outside a trace.
    /// </summary>
    public static void Log(string message, Dictionary<string, object?>? extra = null)
    {
        var active = _currentTrace.Value;
        if (active is null) return;

        var spanId = active.CurrentSpanId();
        if (spanId is null) return;

        foreach (var span in active.Spans.Reverse())
        {
            if (span.SpanId != spanId) continue;

            if (!span.Metadata.TryGetValue("logs", out var raw) || raw is not List<object?> logs)
            {
                logs = new List<object?>();
                span.Metadata["logs"] = logs;
            }

            var entry = new Dictionary<string, object?>
            {
                ["ts_ms"]   = NowMs(),
                ["message"] = Truncate(message, 1024) ?? string.Empty
            };

            if (extra is not null)
                foreach (var (k, v) in extra)
                    entry[k] = v;

            logs.Add(entry);
            return;
        }
    }

    // -------------------------------------------------------------------------
    // Internal helpers called by ActiveTrace / SpanContext
    // -------------------------------------------------------------------------

    internal static void EmitToExporters(SpanData span)
    {
        List<ISpanExporter> snapshot;
        lock (_registryLock) { snapshot = [.._exporters]; }

        foreach (var exporter in snapshot)
        {
            try { exporter.ExportSpan(span); }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine(
                    $"[AgentLens] Exporter error (non-fatal): {ex.Message}");
            }
        }
    }

    internal static void NotifyProcessorsStart(SpanData span)
    {
        List<ISpanProcessor> snapshot;
        lock (_registryLock) { snapshot = [.._processors]; }

        foreach (var proc in snapshot)
        {
            try { proc.OnStart(span); }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine(
                    $"[AgentLens] Processor OnStart error (non-fatal): {ex.Message}");
            }
        }
    }

    internal static void NotifyProcessorsEnd(SpanData span)
    {
        List<ISpanProcessor> snapshot;
        lock (_registryLock) { snapshot = [.._processors]; }

        foreach (var proc in snapshot)
        {
            try { proc.OnEnd(span); }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine(
                    $"[AgentLens] Processor OnEnd error (non-fatal): {ex.Message}");
            }
        }
    }

    internal static long NowMs() =>
        DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

    private static string? Truncate(string? value, int maxLength) =>
        value is null ? null : (value.Length <= maxLength ? value : value[..maxLength]);
}
