"""Google ADK (Agent Development Kit) integration: patch agents and tools for AgentLens.

Supports google-adk >= 0.3 (the decorator-based agent framework).

Install::

    pip install agentlens-observe[google-adk]

Usage::

    from agentlens.integrations.google_adk import patch_google_adk
    patch_google_adk()   # call once at startup

    import agentlens
    agentlens.configure(server_url="http://localhost:3000")

    @agentlens.trace
    def run():
        agent = MyADKAgent()
        agent.run("Hello, agent!")
"""
import logging
import uuid
from typing import Any

from agentlens.tracer import SpanData, _current_trace, _now_ms

logger = logging.getLogger("agentlens.integrations.google_adk")

_patched = False


def patch_google_adk() -> None:
    """Monkey-patch Google ADK Agent and tool invocation for auto-instrumentation.

    Patches:
    - ``Agent.run`` / ``Agent.__call__``  -> emits ``agent_run`` span
    - ``ToolContext.__call__`` / tool functions -> emits ``tool_call`` span

    Safe to call multiple times (idempotent).
    """
    global _patched
    if _patched:
        return

    try:
        import google.adk as adk  # noqa: F401
    except ImportError:
        raise ImportError(
            "google-adk is required: pip install agentlens-observe[google-adk]"
        )

    _patch_agent(adk)
    _patch_tools(adk)
    _patched = True
    logger.info("AgentLens: Google ADK patched successfully")


# ---------------------------------------------------------------------------
# Agent patching
# ---------------------------------------------------------------------------

def _patch_agent(adk: Any) -> None:
    """Patch Agent.run (and __call__ if present) to emit agent_run spans."""
    Agent = getattr(adk, "Agent", None)
    if Agent is None:
        logger.debug("AgentLens: google.adk.Agent not found; skipping agent patch")
        return

    # Prefer `run`; fall back to `__call__` for decorator-style agents
    if hasattr(Agent, "run"):
        _wrap_agent_method(Agent, "run")
    elif hasattr(Agent, "__call__"):
        _wrap_agent_method(Agent, "__call__")
    else:
        logger.debug("AgentLens: Agent has neither .run nor .__call__; skipping")


def _wrap_agent_method(Agent: Any, method_name: str) -> None:
    original = getattr(Agent, method_name)

    def patched(self, *args, **kwargs):
        active = _current_trace.get()
        agent_name = getattr(self, "name", None) or getattr(self, "__class__", type(self)).__name__
        start = _now_ms()

        # Capture input — first positional arg is usually the user message
        input_str = None
        if args:
            input_str = str(args[0])[:1024]
        elif kwargs:
            # Common kwarg names: message, query, input, prompt
            for key in ("message", "query", "input", "prompt"):
                if key in kwargs:
                    input_str = str(kwargs[key])[:1024]
                    break

        result = original(self, *args, **kwargs)

        if active:
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"adk:{agent_name}",
                type="agent_run",
                start_ms=start,
                end_ms=_now_ms(),
                input=input_str,
                output=_extract_output(result),
            )
            active.spans.append(span)
            active.flush_span(span)

        return result

    # Preserve the original for introspection
    patched.__wrapped__ = original  # type: ignore[attr-defined]
    setattr(Agent, method_name, patched)


# ---------------------------------------------------------------------------
# Tool / function patching
# ---------------------------------------------------------------------------

def _patch_tools(adk: Any) -> None:
    """Patch ToolContext or FunctionTool to emit tool_call spans."""
    # Try ToolContext (used in newer ADK versions)
    ToolContext = getattr(adk, "ToolContext", None)
    if ToolContext is not None and hasattr(ToolContext, "__call__"):
        _wrap_tool_context(ToolContext)
        return

    # Try FunctionTool (wraps bare Python functions as ADK tools)
    FunctionTool = getattr(adk, "FunctionTool", None)
    if FunctionTool is not None and hasattr(FunctionTool, "run"):
        _wrap_function_tool(FunctionTool)
        return

    logger.debug("AgentLens: no known tool execution class found in google.adk; skipping tool patch")


def _wrap_tool_context(ToolContext: Any) -> None:
    original_call = ToolContext.__call__

    def patched_call(self, *args, **kwargs):
        active = _current_trace.get()
        tool_name = getattr(self, "name", None) or getattr(self, "tool_name", "adk_tool")
        start = _now_ms()

        result = original_call(self, *args, **kwargs)

        if active:
            input_str = str(args[0])[:1024] if args else None
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"tool:{tool_name}",
                type="tool_call",
                start_ms=start,
                end_ms=_now_ms(),
                input=input_str,
                output=_extract_output(result),
            )
            active.spans.append(span)
            active.flush_span(span)

        return result

    patched_call.__wrapped__ = original_call  # type: ignore[attr-defined]
    ToolContext.__call__ = patched_call


def _wrap_function_tool(FunctionTool: Any) -> None:
    original_run = FunctionTool.run

    def patched_run(self, *args, **kwargs):
        active = _current_trace.get()
        fn = getattr(self, "fn", None) or getattr(self, "func", None)
        tool_name = (fn.__name__ if fn else None) or getattr(self, "name", "adk_fn_tool")
        start = _now_ms()

        result = original_run(self, *args, **kwargs)

        if active:
            input_str = None
            if args:
                input_str = str(args[0])[:1024]
            elif kwargs:
                input_str = str(kwargs)[:1024]

            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"tool:{tool_name}",
                type="tool_call",
                start_ms=start,
                end_ms=_now_ms(),
                input=input_str,
                output=_extract_output(result),
            )
            active.spans.append(span)
            active.flush_span(span)

        return result

    patched_run.__wrapped__ = original_run  # type: ignore[attr-defined]
    FunctionTool.run = patched_run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_output(result: Any) -> str | None:
    """Best-effort extraction of a string output from an ADK result object."""
    if result is None:
        return None
    # Common ADK response attributes
    for attr in ("text", "content", "response", "output", "result"):
        val = getattr(result, attr, None)
        if val is not None:
            return str(val)[:2048]
    return str(result)[:2048]
