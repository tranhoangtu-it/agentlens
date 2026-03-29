namespace AgentLens;

/// <summary>
/// Public contract for a span context returned by AgentLensClient.Span().
/// Both the real SpanContext and the no-op variant implement this interface.
/// </summary>
public interface ISpanContext : IDisposable
{
    ISpanContext SetOutput(string output);
    ISpanContext SetCost(string model, int inputTokens, int outputTokens, double? usd = null);
    ISpanContext SetMetadata(string key, object? value);
    ISpanContext Log(string message, Dictionary<string, object?>? extra = null);
}

/// <summary>
/// Live IDisposable context manager for a manual child span.
/// On Dispose: stamps EndMs, pops from the active stack, flushes to exporters/server.
/// Equivalent to Python's SpanContext class.
///
/// Usage: using var span = AgentLensClient.Span("search", "tool_call");
/// </summary>
public sealed class SpanContext : ISpanContext
{
    private readonly ActiveTrace _active;
    private readonly SpanData _span;
    private bool _disposed;

    internal SpanContext(ActiveTrace active, SpanData span)
    {
        _active = active;
        _span = span;
        _active.PushSpan(_span);
    }

    /// <summary>Sets the output string, truncated to 4096 chars.</summary>
    public ISpanContext SetOutput(string output)
    {
        _span.Output = Truncate(output, 4096);
        return this;
    }

    /// <summary>
    /// Records token cost for this span. Calculates USD automatically from
    /// the model pricing table unless an explicit usd value is provided.
    /// </summary>
    public ISpanContext SetCost(string model, int inputTokens, int outputTokens, double? usd = null)
    {
        _span.Cost = new SpanCost(
            model,
            inputTokens,
            outputTokens,
            usd ?? Cost.CalculateCost(model, inputTokens, outputTokens)
        );
        return this;
    }

    /// <summary>Merges one metadata key-value pair into the span.</summary>
    public ISpanContext SetMetadata(string key, object? value)
    {
        _span.Metadata[key] = value;
        return this;
    }

    /// <summary>
    /// Appends a timestamped log entry to the span's metadata["logs"] list.
    /// </summary>
    public ISpanContext Log(string message, Dictionary<string, object?>? extra = null)
    {
        if (!_span.Metadata.TryGetValue("logs", out var raw) || raw is not List<object?> logs)
        {
            logs = new List<object?>();
            _span.Metadata["logs"] = logs;
        }

        var entry = new Dictionary<string, object?>
        {
            ["ts_ms"]   = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            ["message"] = Truncate(message, 1024) ?? string.Empty
        };

        if (extra is not null)
            foreach (var (k, v) in extra)
                entry[k] = v;

        logs.Add(entry);
        return this;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        _span.EndMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        _active.PopSpan(_span);
        _active.FlushSpan(_span);
    }

    private static string? Truncate(string? value, int maxLength) =>
        value is null ? null : (value.Length <= maxLength ? value : value[..maxLength]);
}

/// <summary>
/// No-op span context returned when Span() is called outside a trace.
/// Silently absorbs all calls rather than throwing. Never modifies any state.
/// </summary>
internal sealed class NoopSpanContext : ISpanContext
{
    internal static readonly NoopSpanContext Instance = new();
    private NoopSpanContext() { }

    public ISpanContext SetOutput(string output) => this;
    public ISpanContext SetCost(string model, int inputTokens, int outputTokens, double? usd = null) => this;
    public ISpanContext SetMetadata(string key, object? value) => this;
    public ISpanContext Log(string message, Dictionary<string, object?>? extra = null) => this;
    public void Dispose() { }
}
