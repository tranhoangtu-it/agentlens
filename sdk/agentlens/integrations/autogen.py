"""AutoGen integration: monkey-patch ConversableAgent to emit AgentLens spans.

Supports AutoGen v0.4+ (autogen-agentchat package).

Install::

    pip install agentlens-observe[autogen]

Usage::

    from agentlens.integrations.autogen import patch_autogen
    patch_autogen()   # call once at startup, before creating any agents

    import agentlens
    agentlens.configure(server_url="http://localhost:3000")

    @agentlens.trace
    def run():
        agent = autogen.ConversableAgent("assistant", ...)
        agent.initiate_chat(...)
"""
import logging
import uuid
from typing import Any

from agentlens.tracer import SpanData, _current_trace, _now_ms

logger = logging.getLogger("agentlens.integrations.autogen")

_patched = False


def patch_autogen() -> None:
    """Monkey-patch AutoGen ConversableAgent for auto-instrumentation.

    Patches:
    - ``ConversableAgent.generate_reply``  -> emits ``agent_run`` span per reply
    - ``ConversableAgent._execute_function`` -> emits ``tool_call`` span per function call

    Safe to call multiple times (idempotent).
    """
    global _patched
    if _patched:
        return
    try:
        import autogen
    except ImportError:
        raise ImportError(
            "autogen-agentchat is required: pip install agentlens-observe[autogen]"
        )

    _patch_generate_reply(autogen.ConversableAgent)
    _patch_execute_function(autogen.ConversableAgent)
    _patched = True
    logger.info("AgentLens: AutoGen patched successfully")


# ---------------------------------------------------------------------------
# Patchers
# ---------------------------------------------------------------------------

def _patch_generate_reply(ConversableAgent: Any) -> None:
    """Wrap generate_reply to create an agent_run span per LLM reply."""
    original = ConversableAgent.generate_reply

    def patched_generate_reply(self, messages=None, sender=None, **kwargs):
        active = _current_trace.get()
        agent_name = getattr(self, "name", "autogen_agent")
        start = _now_ms()

        result = original(self, messages=messages, sender=sender, **kwargs)

        if active:
            # Summarise the last message as input
            last_msg = ""
            if messages:
                last = messages[-1]
                if isinstance(last, dict):
                    last_msg = str(last.get("content", ""))[:1024]
                else:
                    last_msg = str(last)[:1024]

            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"autogen:{agent_name}",
                type="agent_run",
                start_ms=start,
                end_ms=_now_ms(),
                input=last_msg or None,
                output=str(result)[:2048] if result else None,
            )
            active.spans.append(span)
            active.flush_span(span)

        return result

    ConversableAgent.generate_reply = patched_generate_reply


def _patch_execute_function(ConversableAgent: Any) -> None:
    """Wrap _execute_function to create a tool_call span per function invocation."""
    original = getattr(ConversableAgent, "_execute_function", None)
    if original is None:
        # Older AutoGen versions use a different internal name
        original = getattr(ConversableAgent, "execute_function", None)
    if original is None:
        logger.debug("AgentLens: could not find AutoGen function execution method; skipping patch")
        return

    method_name = "_execute_function" if hasattr(ConversableAgent, "_execute_function") else "execute_function"

    def patched_execute_function(self, func_call, **kwargs):
        active = _current_trace.get()
        func_name = func_call.get("name", "unknown") if isinstance(func_call, dict) else str(func_call)
        func_args = func_call.get("arguments", "") if isinstance(func_call, dict) else ""
        start = _now_ms()

        result = original(self, func_call, **kwargs)

        if active:
            # result is typically (bool, dict) — extract content if possible
            output_str = None
            if isinstance(result, tuple) and len(result) == 2:
                _, resp = result
                if isinstance(resp, dict):
                    output_str = str(resp.get("content", resp))[:2048]
                else:
                    output_str = str(resp)[:2048]
            elif result is not None:
                output_str = str(result)[:2048]

            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"tool:{func_name}",
                type="tool_call",
                start_ms=start,
                end_ms=_now_ms(),
                input=str(func_args)[:1024] if func_args else None,
                output=output_str,
            )
            active.spans.append(span)
            active.flush_span(span)

        return result

    setattr(ConversableAgent, method_name, patched_execute_function)
