namespace AgentLens;

/// <summary>
/// Token cost calculator. Prices are USD per 1M tokens (input, output).
/// Port of Python sdk/agentlens/cost.py — last updated 2026-02.
/// </summary>
public static class Cost
{
    // Key: model name (lowercase). Value: (inputPer1M, outputPer1M) in USD.
    private static readonly Dictionary<string, (double Input, double Output)> ModelPrices = new()
    {
        // OpenAI — GPT-4o family
        ["gpt-4o"]            = (2.50,  10.00),
        ["gpt-4o-mini"]       = (0.15,   0.60),
        // OpenAI — GPT-4.1 family (2025)
        ["gpt-4.1"]           = (2.00,   8.00),
        ["gpt-4.1-mini"]      = (0.40,   1.60),
        ["gpt-4.1-nano"]      = (0.10,   0.40),
        // OpenAI — GPT-4.5
        ["gpt-4.5-preview"]   = (75.00, 150.00),
        // OpenAI — legacy
        ["gpt-4-turbo"]       = (10.00,  30.00),
        ["gpt-3.5-turbo"]     = ( 0.50,   1.50),
        // OpenAI — reasoning
        ["o1"]                = (15.00,  60.00),
        ["o1-mini"]           = ( 3.00,  12.00),
        ["o3-mini"]           = ( 1.10,   4.40),
        ["o3"]                = (10.00,  40.00),
        // Anthropic — Claude 3.5
        ["claude-3-5-sonnet"] = ( 3.00,  15.00),
        ["claude-3-5-haiku"]  = ( 0.80,   4.00),
        ["claude-3-opus"]     = (15.00,  75.00),
        // Anthropic — Claude 4 (2025)
        ["claude-sonnet-4"]   = ( 3.00,  15.00),
        ["claude-haiku-4"]    = ( 0.80,   4.00),
        ["claude-opus-4"]     = (15.00,  75.00),
        // Google — Gemini 1.5
        ["gemini-1.5-pro"]    = ( 3.50,  10.50),
        ["gemini-1.5-flash"]  = ( 0.075,  0.30),
        // Google — Gemini 2.0 (2025)
        ["gemini-2.0-flash"]  = ( 0.10,   0.40),
        ["gemini-2.0-pro"]    = ( 1.25,  10.00),
        // DeepSeek
        ["deepseek-v3"]       = ( 0.27,   1.10),
        ["deepseek-r1"]       = ( 0.55,   2.19),
        // Meta — Llama (via providers)
        ["llama-3.1-70b"]     = ( 0.52,   0.75),
        ["llama-3.1-405b"]    = ( 3.00,   3.00),
        ["llama-3.3-70b"]     = ( 0.39,   0.59),
    };

    /// <summary>
    /// Returns USD cost for a model call, or null if the model is unknown.
    /// Strips provider prefix (e.g. "openai/gpt-4o" → "gpt-4o") and does
    /// prefix matching as fallback, mirroring Python SDK behaviour.
    /// </summary>
    public static double? CalculateCost(string model, int inputTokens, int outputTokens)
    {
        // Strip provider prefix: "openai/gpt-4o" → "gpt-4o"
        var key = model.Split('/')[^1].ToLowerInvariant();

        if (!ModelPrices.TryGetValue(key, out var prices))
        {
            // Prefix fallback: match "gpt-4o-2024-05-13" → "gpt-4o"
            foreach (var (k, v) in ModelPrices)
            {
                if (key.StartsWith(k, StringComparison.Ordinal) ||
                    k.StartsWith(key, StringComparison.Ordinal))
                {
                    prices = v;
                    break;
                }
            }

            if (prices == default) return null;
        }

        var usd = (inputTokens * prices.Input + outputTokens * prices.Output) / 1_000_000.0;
        return Math.Round(usd, 6);
    }
}
