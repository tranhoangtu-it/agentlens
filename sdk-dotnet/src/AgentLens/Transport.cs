using System.Net.Http.Json;
using System.Text.Json;

namespace AgentLens;

/// <summary>
/// Fire-and-forget HTTP transport. Posts traces and span batches to the
/// AgentLens server without blocking the caller.
/// Equivalent to Python's transport.py.
/// </summary>
internal static class Transport
{
    // Shared client — thread-safe, reuse across calls
    private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(5) };

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
    };

    private static string _serverUrl = Environment.GetEnvironmentVariable("AGENTLENS_URL")
                                        ?? "http://localhost:3000";

    internal static void SetServerUrl(string url) =>
        _serverUrl = url.TrimEnd('/');

    /// <summary>
    /// Queues a full trace POST to /api/traces in a background task.
    /// Never throws; errors are swallowed and logged to debug output.
    /// </summary>
    internal static void PostTrace(string traceId, string agentName, IEnumerable<SpanData> spans)
    {
        var payload = new TracePayload(traceId, agentName, spans.ToArray());
        var url = _serverUrl + "/api/traces";
        FireAndForget(url, payload);
    }

    /// <summary>
    /// Queues a streaming span POST to /api/traces/{traceId}/spans.
    /// Used in streaming mode to deliver completed spans immediately.
    /// </summary>
    internal static void PostSpans(string traceId, IEnumerable<SpanData> spans)
    {
        var payload = new SpanBatchPayload(spans.ToArray());
        var url = $"{_serverUrl}/api/traces/{traceId}/spans";
        FireAndForget(url, payload);
    }

    private static void FireAndForget<T>(string url, T payload)
    {
        // Capture values; lambda must not close over mutable state
        _ = Task.Run(async () =>
        {
            try
            {
                var response = await _http.PostAsJsonAsync(url, payload, _jsonOptions)
                                          .ConfigureAwait(false);
                if (!response.IsSuccessStatusCode)
                    System.Diagnostics.Debug.WriteLine(
                        $"[AgentLens] Server returned {(int)response.StatusCode} for {url}");
            }
            catch (Exception ex)
            {
                // Non-fatal — SDK must never crash host application
                System.Diagnostics.Debug.WriteLine(
                    $"[AgentLens] Transport error (non-fatal): {ex.Message}");
            }
        });
    }

    // JSON payload shapes — internal, serialized with snake_case via JsonPropertyName on SpanData

    private sealed record TracePayload(
        [property: System.Text.Json.Serialization.JsonPropertyName("trace_id")]   string TraceId,
        [property: System.Text.Json.Serialization.JsonPropertyName("agent_name")] string AgentName,
        [property: System.Text.Json.Serialization.JsonPropertyName("spans")]      SpanData[] Spans
    );

    private sealed record SpanBatchPayload(
        [property: System.Text.Json.Serialization.JsonPropertyName("spans")] SpanData[] Spans
    );
}
