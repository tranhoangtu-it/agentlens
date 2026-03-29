namespace AgentLens;

/// <summary>
/// Span lifecycle hooks — observe or mutate spans while they are in-flight.
/// Processors fire synchronously during PushSpan/PopSpan, so implementations
/// must be fast and must not throw.
/// Equivalent to Python's SpanProcessor protocol.
/// </summary>
public interface ISpanProcessor
{
    /// <summary>
    /// Called when a span starts (pushed onto the active stack). Must not throw.
    /// </summary>
    void OnStart(SpanData span);

    /// <summary>
    /// Called when a span ends (popped from the active stack). Must not throw.
    /// </summary>
    void OnEnd(SpanData span);
}
