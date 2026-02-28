"""Token cost table. Update periodically from provider pricing pages."""
from typing import Optional

# USD per 1M tokens — (input_price, output_price)
# Last updated: 2026-02
MODEL_PRICES: dict[str, tuple[float, float]] = {
    # OpenAI — GPT-4o family
    "gpt-4o":            (2.50,  10.00),
    "gpt-4o-mini":       (0.15,   0.60),
    # OpenAI — GPT-4.1 family (2025)
    "gpt-4.1":           (2.00,   8.00),
    "gpt-4.1-mini":      (0.40,   1.60),
    "gpt-4.1-nano":      (0.10,   0.40),
    # OpenAI — GPT-4.5
    "gpt-4.5-preview":   (75.00, 150.00),
    # OpenAI — legacy
    "gpt-4-turbo":       (10.00, 30.00),
    "gpt-3.5-turbo":     (0.50,   1.50),
    # OpenAI — reasoning
    "o1":                (15.00, 60.00),
    "o1-mini":           (3.00,  12.00),
    "o3-mini":           (1.10,   4.40),
    "o3":                (10.00, 40.00),
    # Anthropic — Claude 3.5
    "claude-3-5-sonnet": (3.00,  15.00),
    "claude-3-5-haiku":  (0.80,   4.00),
    "claude-3-opus":     (15.00, 75.00),
    # Anthropic — Claude 4 (2025)
    "claude-sonnet-4":   (3.00,  15.00),
    "claude-haiku-4":    (0.80,   4.00),
    "claude-opus-4":     (15.00, 75.00),
    # Google — Gemini 1.5
    "gemini-1.5-pro":    (3.50,  10.50),
    "gemini-1.5-flash":  (0.075,  0.30),
    # Google — Gemini 2.0 (2025)
    "gemini-2.0-flash":  (0.10,   0.40),
    "gemini-2.0-pro":    (1.25,  10.00),
    # DeepSeek
    "deepseek-v3":       (0.27,   1.10),
    "deepseek-r1":       (0.55,   2.19),
    # Meta — Llama (via providers)
    "llama-3.1-70b":     (0.52,   0.75),
    "llama-3.1-405b":    (3.00,   3.00),
    "llama-3.3-70b":     (0.39,   0.59),
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Optional[float]:
    """Return USD cost for a model call. Returns None if model unknown."""
    # Fuzzy match: strip provider prefix (e.g. "openai/gpt-4o" -> "gpt-4o")
    key = model.split("/")[-1].lower()
    # Try exact, then prefix match
    prices = MODEL_PRICES.get(key)
    if not prices:
        for k, v in MODEL_PRICES.items():
            if key.startswith(k) or k.startswith(key):
                prices = v
                break
    if not prices:
        return None
    in_price, out_price = prices
    usd = (input_tokens * in_price + output_tokens * out_price) / 1_000_000
    return round(usd, 6)
