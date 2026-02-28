"""Maps OTLP HTTP JSON payload to AgentLens internal span dicts."""

from typing import Any

# OTel SpanKind int → AgentLens span type
_KIND_MAP: dict[int, str] = {
    0: "task",
    1: "llm_call",
    2: "agent_run",
    3: "tool_call",
    4: "task",
    5: "task",
}


def _attrs_to_dict(attributes: list[dict]) -> dict[str, Any]:
    """Convert OTel attribute list to flat Python dict."""
    result = {}
    for attr in attributes:
        key = attr.get("key", "")
        val_obj = attr.get("value", {})
        # Pick the first non-empty value type present
        for vtype in ("stringValue", "intValue", "doubleValue", "boolValue"):
            if vtype in val_obj:
                result[key] = val_obj[vtype]
                break
    return result


def _get_resource_attr(resource: dict, key: str, default: str = "") -> str:
    """Extract a string attribute from OTel resource."""
    for attr in resource.get("attributes", []):
        if attr.get("key") == key:
            return attr.get("value", {}).get("stringValue", default)
    return default


def _ns_to_ms(ns_str: "str | int | None") -> "int | None":
    """Convert nanosecond timestamp string/int to milliseconds. Returns None if falsy."""
    if not ns_str:
        return None
    try:
        ms = int(ns_str) // 1_000_000
        return ms if ms > 0 else None
    except (ValueError, TypeError):
        return None


def map_otlp_request(body: dict) -> list[tuple[str, str, list[dict]]]:
    """
    Parse OTLP HTTP JSON body.

    Returns list of (trace_id, agent_name, spans_data) tuples — one per unique
    trace_id found within a resourceSpan block.
    Each spans_data item is a dict matching storage.create_trace / add_spans_to_trace
    expectations (keys: span_id, parent_id, name, type, start_ms, end_ms, input,
    output, cost, metadata).
    """
    groups: list[tuple[str, str, list[dict]]] = []

    for resource_span in body.get("resourceSpans", []):
        resource = resource_span.get("resource", {})
        agent_name = _get_resource_attr(resource, "service.name") or "otel"

        # Collect all spans across all scopes, grouped by trace_id
        trace_spans: dict[str, list[dict]] = {}

        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                trace_id: str = span.get("traceId", "")
                if not trace_id:
                    continue  # skip malformed spans

                parent_id = span.get("parentSpanId") or None  # "" → None

                attrs = _attrs_to_dict(span.get("attributes", []))
                # Pull well-known keys out; rest become metadata
                input_val = attrs.pop("input", None)
                output_val = attrs.pop("output", None)
                # Stringify input/output if not already str
                if input_val is not None and not isinstance(input_val, str):
                    input_val = str(input_val)
                if output_val is not None and not isinstance(output_val, str):
                    output_val = str(output_val)

                span_dict = {
                    "span_id": span.get("spanId", ""),
                    "parent_id": parent_id,
                    "name": span.get("name", "unknown"),
                    "type": _KIND_MAP.get(span.get("kind", 0), "task"),
                    "start_ms": _ns_to_ms(span.get("startTimeUnixNano")) or 0,
                    "end_ms": _ns_to_ms(span.get("endTimeUnixNano")),
                    "input": input_val,
                    "output": output_val,
                    "cost": None,
                    "metadata": attrs if attrs else None,
                }

                trace_spans.setdefault(trace_id, []).append(span_dict)

        for trace_id, spans in trace_spans.items():
            groups.append((trace_id, agent_name, spans))

    return groups
