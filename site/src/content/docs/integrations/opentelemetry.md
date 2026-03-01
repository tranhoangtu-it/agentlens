---
title: OpenTelemetry
description: Export AgentLens spans to OTel backends, or ingest OTel spans into AgentLens
---

AgentLens supports OpenTelemetry in two directions:

1. **Export** — bridge AgentLens spans to any OTel-compatible backend (Jaeger, Tempo, DataDog, etc.)
2. **Ingest** — receive OTLP HTTP JSON spans from any OTel-instrumented app

## Export: AgentLens → OTel Backend

```python
from agentlens.exporters.otel import AgentLensOTelExporter
import agentlens

agentlens.configure(server_url="http://localhost:3000")
agentlens.add_exporter(AgentLensOTelExporter())

# Now spans are sent to both AgentLens AND your OTel backend
@agentlens.trace(name="MyAgent")
def run():
    with agentlens.span("search", "tool_call") as s:
        result = do_search()
        s.set_output(result)
```

## Ingest: OTel App → AgentLens

Any app instrumented with the OpenTelemetry SDK can send spans directly to AgentLens via the OTLP HTTP JSON endpoint.

### Environment Variable Configuration

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:3000/api/otel
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
```

### Manual OTLP Push

```python
import requests

requests.post("http://localhost:3000/api/otel/v1/traces", json={
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "my-agent"}}
            ]
        },
        "scopeSpans": [{
            "spans": [{
                "traceId": "abc123",
                "spanId": "span001",
                "parentSpanId": "",
                "name": "agent_run",
                "kind": 2,
                "startTimeUnixNano": "1700000000000000000",
                "endTimeUnixNano": "1700000001000000000",
                "attributes": [],
                "status": {"code": 1}
            }]
        }]
    }]
})
```

## Span Kind Mapping

OTel span kinds are mapped to AgentLens span types:

| OTel Kind | AgentLens Type |
|-----------|---------------|
| `SERVER` (2) | `agent_run` |
| `CLIENT` (3) | `tool_call` |
| `INTERNAL` (1) | `llm_call` |
| anything else | `task` |

The `service.name` resource attribute becomes the `agent_name` in AgentLens (fallback: `"otel"`).

## Supported Protocol

AgentLens accepts **OTLP HTTP JSON** only. gRPC and binary protobuf are not supported.
