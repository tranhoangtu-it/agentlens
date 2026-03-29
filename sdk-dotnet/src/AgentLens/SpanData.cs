using System.Text.Json.Serialization;

namespace AgentLens;

/// <summary>
/// Immutable snapshot of a single span within a trace.
/// Mutable fields (EndMs, Input, Output, Cost, Metadata) are set during span lifecycle.
/// </summary>
public sealed class SpanData
{
    [JsonPropertyName("span_id")]
    public string SpanId { get; init; }

    [JsonPropertyName("parent_id")]
    public string? ParentId { get; init; }

    [JsonPropertyName("name")]
    public string Name { get; init; }

    [JsonPropertyName("type")]
    public string Type { get; init; }

    [JsonPropertyName("start_ms")]
    public long StartMs { get; init; }

    [JsonPropertyName("end_ms")]
    public long? EndMs { get; set; }

    [JsonPropertyName("input")]
    public string? Input { get; set; }

    [JsonPropertyName("output")]
    public string? Output { get; set; }

    [JsonPropertyName("cost")]
    public SpanCost? Cost { get; set; }

    [JsonPropertyName("metadata")]
    public Dictionary<string, object?> Metadata { get; init; } = new();

    public SpanData(string spanId, string? parentId, string name, string type, long startMs)
    {
        SpanId = spanId;
        ParentId = parentId;
        Name = name;
        Type = type;
        StartMs = startMs;
    }
}

/// <summary>
/// Cost breakdown for a single LLM call within a span.
/// </summary>
public sealed class SpanCost
{
    [JsonPropertyName("model")]
    public string Model { get; init; }

    [JsonPropertyName("input_tokens")]
    public int InputTokens { get; init; }

    [JsonPropertyName("output_tokens")]
    public int OutputTokens { get; init; }

    [JsonPropertyName("usd")]
    public double? Usd { get; init; }

    public SpanCost(string model, int inputTokens, int outputTokens, double? usd)
    {
        Model = model;
        InputTokens = inputTokens;
        OutputTokens = outputTokens;
        Usd = usd;
    }
}
