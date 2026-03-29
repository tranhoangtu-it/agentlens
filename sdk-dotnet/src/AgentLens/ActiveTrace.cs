namespace AgentLens;

/// <summary>
/// Holds the live state of a single trace: all spans collected so far and the
/// currently-active span stack. One instance per logical agent run.
/// </summary>
public sealed class ActiveTrace
{
    public string TraceId { get; }
    public string AgentName { get; }
    public bool Streaming { get; }

    private readonly List<SpanData> _spans = new();
    private readonly Stack<string> _spanStack = new();
    private readonly object _lock = new();

    public IReadOnlyList<SpanData> Spans
    {
        get { lock (_lock) { return _spans.ToList(); } }
    }

    public ActiveTrace(string traceId, string agentName, bool streaming = false)
    {
        TraceId = traceId;
        AgentName = agentName;
        Streaming = streaming;
    }

    /// <summary>Returns the span ID at the top of the stack, or null if empty.</summary>
    public string? CurrentSpanId()
    {
        lock (_lock)
        {
            return _spanStack.Count > 0 ? _spanStack.Peek() : null;
        }
    }

    /// <summary>Appends the span to the trace and pushes its ID onto the active stack.</summary>
    internal void PushSpan(SpanData span)
    {
        lock (_lock)
        {
            _spans.Add(span);
            _spanStack.Push(span.SpanId);
        }
        AgentLensClient.NotifyProcessorsStart(span);
    }

    /// <summary>Pops the top span ID from the stack and fires processor on_end.</summary>
    internal void PopSpan(SpanData span)
    {
        lock (_lock)
        {
            if (_spanStack.Count > 0)
                _spanStack.Pop();
        }
        AgentLensClient.NotifyProcessorsEnd(span);
    }

    /// <summary>
    /// Emits a single completed span to exporters and, in streaming mode,
    /// posts it to the server immediately without waiting for trace completion.
    /// </summary>
    internal void FlushSpan(SpanData span)
    {
        AgentLensClient.EmitToExporters(span);
        if (Streaming)
            Transport.PostSpans(TraceId, new[] { span });
    }

    /// <summary>Sends the full trace batch to the server. Exports all spans first.</summary>
    internal void Flush()
    {
        List<SpanData> snapshot;
        lock (_lock) { snapshot = _spans.ToList(); }

        foreach (var span in snapshot)
            AgentLensClient.EmitToExporters(span);

        Transport.PostTrace(TraceId, AgentName, snapshot);
    }
}
