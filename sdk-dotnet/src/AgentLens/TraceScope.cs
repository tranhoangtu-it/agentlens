namespace AgentLens;

/// <summary>
/// IDisposable scope returned by AgentLensClient.Trace().
/// On Dispose: stamps the root span EndMs, flushes all spans to the server,
/// and clears the AsyncLocal trace context.
///
///   using (AgentLensClient.Trace("my-agent")) { ... }
/// </summary>
public sealed class TraceScope : IDisposable
{
    private readonly ActiveTrace _active;
    private readonly SpanData _rootSpan;
    private readonly AsyncLocal<ActiveTrace?> _context;
    private bool _disposed;

    internal TraceScope(ActiveTrace active, SpanData rootSpan, AsyncLocal<ActiveTrace?> context)
    {
        _active   = active;
        _rootSpan = rootSpan;
        _context  = context;
    }

    /// <summary>
    /// Optionally record the root span's output before the trace closes.
    /// Truncated to 4096 chars.
    /// </summary>
    public TraceScope SetOutput(string output)
    {
        _rootSpan.Output = output.Length <= 4096 ? output : output[..4096];
        return this;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        _rootSpan.EndMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        _active.PopSpan(_rootSpan);
        _active.Flush();

        // Clear context so callers outside this scope see null
        _context.Value = null;
    }
}
