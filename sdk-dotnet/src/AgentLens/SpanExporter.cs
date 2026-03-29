namespace AgentLens;

/// <summary>
/// Optional span exporter — receives every completed span in addition to the
/// normal AgentLens HTTP transport. Implement to forward spans to OpenTelemetry,
/// custom sinks, etc. Multiple exporters can be registered.
/// Equivalent to Python's SpanExporter protocol.
/// </summary>
public interface ISpanExporter
{
    /// <summary>
    /// Called after each span completes. Must not throw.
    /// </summary>
    void ExportSpan(SpanData span);

    /// <summary>
    /// Called on application shutdown. Flush any buffered state.
    /// </summary>
    void Shutdown();
}
