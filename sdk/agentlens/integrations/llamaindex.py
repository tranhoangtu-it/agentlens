"""LlamaIndex integration: callback handler that emits AgentLens spans.

Supports llama-index-core >= 0.11 (the modular package layout).

Install::

    pip install agentlens-observe[llamaindex]

Usage::

    from agentlens.integrations.llamaindex import AgentLensCallbackHandler
    from llama_index.core import Settings
    from llama_index.core.callbacks import CallbackManager

    handler = AgentLensCallbackHandler()
    Settings.callback_manager = CallbackManager([handler])

    import agentlens
    agentlens.configure(server_url="http://localhost:3000")

    @agentlens.trace
    def run():
        index.as_query_engine().query("What is RAG?")
"""
import logging
import uuid
from typing import Any, Optional

try:
    from llama_index.core.callbacks.base import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType, EventPayload
except ImportError:
    raise ImportError(
        "llama-index-core is required: pip install agentlens-observe[llamaindex]"
    )

from agentlens.tracer import SpanData, _current_trace, _now_ms
from agentlens.cost import calculate_cost

logger = logging.getLogger("agentlens.integrations.llamaindex")

# Map LlamaIndex event types to AgentLens span types
_EVENT_TYPE_MAP: dict[str, str] = {
    CBEventType.LLM: "llm_call",
    CBEventType.QUERY: "agent_run",
    CBEventType.RETRIEVE: "tool_call",
    CBEventType.SYNTHESIZE: "tool_call",
    CBEventType.EMBEDDING: "tool_call",
    CBEventType.CHUNKING: "tool_call",
    CBEventType.NODE_PARSING: "tool_call",
    CBEventType.TREE: "tool_call",
    CBEventType.SUB_QUESTION: "tool_call",
    CBEventType.AGENT_STEP: "agent_run",
    CBEventType.FUNCTION_CALL: "tool_call",
}

# Human-readable prefix for span names
_EVENT_NAME_PREFIX: dict[str, str] = {
    CBEventType.LLM: "llm",
    CBEventType.QUERY: "query",
    CBEventType.RETRIEVE: "retrieve",
    CBEventType.SYNTHESIZE: "synthesize",
    CBEventType.EMBEDDING: "embed",
    CBEventType.CHUNKING: "chunk",
    CBEventType.NODE_PARSING: "parse",
    CBEventType.TREE: "tree",
    CBEventType.SUB_QUESTION: "sub_question",
    CBEventType.AGENT_STEP: "agent_step",
    CBEventType.FUNCTION_CALL: "fn_call",
}


class AgentLensCallbackHandler(BaseCallbackHandler):
    """Drop-in LlamaIndex callback handler that records spans into AgentLens.

    Handles both start and end events for LLM calls, retrieval, queries, and
    agent steps.  Token costs are extracted from LLM end payloads when available.
    """

    def __init__(self) -> None:
        # event_id -> (start_ms, event_type, span_name)
        self._pending: dict[str, tuple[int, str, str]] = {}
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[],
        )

    # ------------------------------------------------------------------
    # BaseCallbackHandler interface
    # ------------------------------------------------------------------

    def on_event_start(
        self,
        event_type: CBEventType,
        payload: Optional[dict] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        span_name = self._build_span_name(event_type, payload)
        self._pending[event_id] = (_now_ms(), event_type, span_name)
        return event_id

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: Optional[dict] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        active = _current_trace.get()
        if not active:
            self._pending.pop(event_id, None)
            return

        entry = self._pending.pop(event_id, None)
        if entry is None:
            return

        start_ms, ev_type, span_name = entry
        span_type = _EVENT_TYPE_MAP.get(ev_type, "tool_call")
        payload = payload or {}

        input_str, output_str, cost = self._extract_io_and_cost(ev_type, payload)

        span = SpanData(
            span_id=str(uuid.uuid4()),
            parent_id=active.current_span_id(),
            name=span_name,
            type=span_type,
            start_ms=start_ms,
            end_ms=_now_ms(),
            input=input_str,
            output=output_str,
            cost=cost,
        )
        active.spans.append(span)
        active.flush_span(span)

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Called at the beginning of a LlamaIndex trace — no-op for us."""

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[dict] = None,
    ) -> None:
        """Called at the end of a LlamaIndex trace — no-op for us."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_span_name(
        self, event_type: CBEventType, payload: Optional[dict]
    ) -> str:
        prefix = _EVENT_NAME_PREFIX.get(event_type, str(event_type).lower())
        payload = payload or {}

        # Try to enrich the name with model or query info
        if event_type == CBEventType.LLM:
            model = (
                payload.get("serialized", {}).get("model", "")
                or payload.get("model", "")
            )
            return f"llm:{model}" if model else "llm:call"

        if event_type == CBEventType.QUERY:
            q = payload.get(EventPayload.QUERY_STR, "")
            return f"query:{str(q)[:40]}" if q else "query"

        if event_type == CBEventType.FUNCTION_CALL:
            fn = payload.get("function_call", {})
            name = fn.get("name", "") if isinstance(fn, dict) else str(fn)[:40]
            return f"fn_call:{name}" if name else "fn_call"

        return prefix

    def _extract_io_and_cost(
        self, event_type: CBEventType, payload: dict
    ) -> tuple[Optional[str], Optional[str], Optional[dict]]:
        """Return (input_str, output_str, cost_dict) from an end-event payload."""
        input_str: Optional[str] = None
        output_str: Optional[str] = None
        cost: Optional[dict] = None

        if event_type == CBEventType.LLM:
            # Input: messages list
            messages = payload.get(EventPayload.MESSAGES, [])
            if messages:
                input_str = str(messages[-1])[:1024] if messages else None

            # Output: response object
            response = payload.get(EventPayload.RESPONSE)
            if response is not None:
                output_str = str(getattr(response, "text", response))[:2048]

            # Cost: token usage
            raw_usage = payload.get("usage") or getattr(response, "raw", {})
            if isinstance(raw_usage, dict):
                in_tok = raw_usage.get("prompt_tokens", 0) or raw_usage.get("input_tokens", 0)
                out_tok = raw_usage.get("completion_tokens", 0) or raw_usage.get("output_tokens", 0)
            else:
                in_tok, out_tok = 0, 0

            if in_tok or out_tok:
                model = (
                    payload.get("serialized", {}).get("model", "")
                    or payload.get("model", "unknown")
                )
                usd = calculate_cost(model, in_tok, out_tok)
                cost = {
                    "model": model,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "usd": usd,
                }

        elif event_type == CBEventType.QUERY:
            q = payload.get(EventPayload.QUERY_STR)
            if q:
                input_str = str(q)[:1024]
            resp = payload.get(EventPayload.RESPONSE)
            if resp is not None:
                output_str = str(getattr(resp, "response", resp))[:2048]

        elif event_type == CBEventType.RETRIEVE:
            q = payload.get(EventPayload.QUERY_STR)
            if q:
                input_str = str(q)[:1024]
            nodes = payload.get(EventPayload.NODES, [])
            if nodes:
                output_str = f"{len(nodes)} nodes retrieved"

        elif event_type == CBEventType.FUNCTION_CALL:
            fn = payload.get("function_call", {})
            if isinstance(fn, dict):
                input_str = str(fn.get("arguments", ""))[:1024]
            output_str = str(payload.get("function_call_response", ""))[:2048] or None

        return input_str, output_str, cost
