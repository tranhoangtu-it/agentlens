"""LLM-as-Judge evaluation runner — build judge prompt, call LLM, parse score."""

import json
import logging
from typing import Optional

from eval_models import EvalCriteria
from llm_provider import call_llm, LLMProviderError
from models import Span, Trace

logger = logging.getLogger(__name__)


def _build_judge_prompt(criteria: EvalCriteria, trace: Trace, spans: list[Span]) -> str:
    """Build the user prompt for the LLM judge."""
    # Extract final output from the root span (first span without parent)
    agent_output = ""
    for s in spans:
        if not s.parent_id and s.output:
            agent_output = s.output[:2000]
            break

    # If no root span output, collect all span outputs
    if not agent_output:
        outputs = [f"[{s.name}] {s.output[:500]}" for s in spans if s.output]
        agent_output = "\n".join(outputs[:10]) or "(no output captured)"

    score_instruction = (
        "Score from 1 to 5 (1=worst, 5=best)"
        if criteria.score_type == "numeric"
        else "Score as 1 (pass) or 0 (fail)"
    )

    return f"""## Agent Trace
Agent: {trace.agent_name}
Status: {trace.status}
Duration: {trace.duration_ms}ms
Spans: {trace.span_count}

## Agent Output
{agent_output}

## Evaluation Criteria
Name: {criteria.name}
Description: {criteria.description}

## Rubric
{criteria.rubric}

## Instructions
{score_instruction}

Respond ONLY with valid JSON:
{{"score": <number>, "reasoning": "<1-2 sentence explanation>"}}"""


_SYSTEM_PROMPT = (
    "You are an evaluation judge. Assess the agent's output against the given criteria and rubric. "
    "Be objective and concise. Respond ONLY with valid JSON."
)


def run_eval(
    criteria: EvalCriteria,
    trace: Trace,
    spans: list[Span],
    provider: str,
    api_key: str,
    model: str,
) -> dict:
    """Run a single evaluation. Returns {score, reasoning}.

    Raises LLMProviderError on failure.
    """
    user_prompt = _build_judge_prompt(criteria, trace, spans)
    response_text = call_llm(
        provider=provider,
        api_key=api_key,
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_mode=(provider == "openai"),
    )

    # Parse JSON response
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        score = float(data.get("score", 0))
        # Clamp score to valid range
        if criteria.score_type == "numeric":
            score = max(1.0, min(5.0, score))
        else:
            score = 1.0 if score >= 0.5 else 0.0

        return {
            "score": score,
            "reasoning": str(data.get("reasoning", "No reasoning provided"))[:2000],
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.warning("Failed to parse eval response: %s", e)
        return {
            "score": 0.0,
            "reasoning": f"Failed to parse LLM response: {response_text[:500]}",
        }
