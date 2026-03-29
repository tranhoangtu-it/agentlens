using Xunit;

namespace AgentLens.Tests;

public sealed class CostTests
{
    [Theory]
    [InlineData("gpt-4o",            1000, 500,  0.007500)]
    [InlineData("gpt-4o-mini",       1000, 500,  0.000450)]
    [InlineData("claude-3-5-sonnet", 1000, 500,  0.010500)]
    [InlineData("claude-sonnet-4",   1000, 500,  0.010500)]
    [InlineData("o1",                1000, 500,  0.045000)]
    [InlineData("gemini-2.0-flash",  1000, 500,  0.000300)]
    public void CalculateCost_KnownModel_ReturnsCorrectUsd(
        string model, int inputTokens, int outputTokens, double expectedUsd)
    {
        var result = Cost.CalculateCost(model, inputTokens, outputTokens);
        Assert.NotNull(result);
        Assert.Equal(expectedUsd, result!.Value, precision: 6);
    }

    [Fact]
    public void CalculateCost_UnknownModel_ReturnsNull()
    {
        var result = Cost.CalculateCost("unknown-model-xyz", 1000, 500);
        Assert.Null(result);
    }

    [Fact]
    public void CalculateCost_StripsProviderPrefix()
    {
        // "openai/gpt-4o" should resolve identically to "gpt-4o"
        var withPrefix    = Cost.CalculateCost("openai/gpt-4o", 1000, 500);
        var withoutPrefix = Cost.CalculateCost("gpt-4o",        1000, 500);
        Assert.NotNull(withPrefix);
        Assert.Equal(withoutPrefix, withPrefix);
    }

    [Fact]
    public void CalculateCost_PrefixMatch_ResolvesVersionedModel()
    {
        // "gpt-4o-2024-05-13" should prefix-match to "gpt-4o"
        var versioned = Cost.CalculateCost("gpt-4o-2024-05-13", 1000, 500);
        var base_     = Cost.CalculateCost("gpt-4o",            1000, 500);
        Assert.NotNull(versioned);
        Assert.Equal(base_, versioned);
    }

    [Fact]
    public void CalculateCost_ZeroTokens_ReturnsZero()
    {
        var result = Cost.CalculateCost("gpt-4o", 0, 0);
        Assert.NotNull(result);
        Assert.Equal(0.0, result!.Value, precision: 6);
    }

    [Fact]
    public void CalculateCost_CaseInsensitive()
    {
        var lower = Cost.CalculateCost("GPT-4O", 1000, 500);
        var normal = Cost.CalculateCost("gpt-4o", 1000, 500);
        Assert.Equal(normal, lower);
    }

    [Theory]
    [InlineData("deepseek-v3",   1000, 500, 0.000820)]
    [InlineData("llama-3.3-70b", 1000, 500, 0.000685)]
    public void CalculateCost_NonOpenAiModels_ReturnsCorrectUsd(
        string model, int inputTokens, int outputTokens, double expectedUsd)
    {
        var result = Cost.CalculateCost(model, inputTokens, outputTokens);
        Assert.NotNull(result);
        Assert.Equal(expectedUsd, result!.Value, precision: 6);
    }
}
