"""Tests for OTel OTLP HTTP ingestion — mapper unit tests + endpoint integration."""

import pytest
from otel_mapper import map_otlp_request, _ns_to_ms, _get_resource_attr


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_otlp_body(
    trace_id: str = "abc123",
    span_id: str = "span001",
    parent_span_id: str = "",
    service_name: str = "my-agent",
    kind: int = 2,
    start_ns: str = "1700000000000000000",
    end_ns: str = "1700000001000000000",
    extra_attrs: list | None = None,
) -> dict:
    attrs = extra_attrs or []
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service_name}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "parentSpanId": parent_span_id,
                                "name": "do_work",
                                "kind": kind,
                                "startTimeUnixNano": start_ns,
                                "endTimeUnixNano": end_ns,
                                "attributes": attrs,
                                "status": {"code": 1},
                            }
                        ]
                    }
                ],
            }
        ]
    }


# ── Unit tests — otel_mapper (no DB) ─────────────────────────────────────────


class TestOtelMapperUnit:
    def test_empty_body(self):
        """Empty body returns empty list — no crash."""
        assert map_otlp_request({}) == []

    def test_single_span_mapping(self):
        """Basic field mapping: trace_id, agent_name, kind→type, ns→ms."""
        body = _make_otlp_body(
            trace_id="trace-abc",
            span_id="span-001",
            service_name="search-agent",
            kind=2,  # SERVER → agent_run
            start_ns="1700000000000000000",
            end_ns="1700000001000000000",
        )
        groups = map_otlp_request(body)
        assert len(groups) == 1
        trace_id, agent_name, spans = groups[0]

        assert trace_id == "trace-abc"
        assert agent_name == "search-agent"
        assert len(spans) == 1

        s = spans[0]
        assert s["span_id"] == "span-001"
        assert s["type"] == "agent_run"
        assert s["start_ms"] == 1_700_000_000_000
        assert s["end_ms"] == 1_700_000_001_000
        assert s["name"] == "do_work"

    def test_parent_span_id_empty_string_becomes_none(self):
        """OTel root spans have parentSpanId='', must map to None."""
        body = _make_otlp_body(parent_span_id="")
        _, _, spans = map_otlp_request(body)[0]
        assert spans[0]["parent_id"] is None

    def test_input_output_extracted_from_attributes(self):
        """'input' and 'output' attrs become top-level fields, not metadata."""
        attrs = [
            {"key": "input", "value": {"stringValue": "hello"}},
            {"key": "output", "value": {"stringValue": "world"}},
            {"key": "custom_key", "value": {"stringValue": "custom_val"}},
        ]
        body = _make_otlp_body(extra_attrs=attrs)
        _, _, spans = map_otlp_request(body)[0]
        s = spans[0]

        assert s["input"] == "hello"
        assert s["output"] == "world"
        # input/output should NOT appear in metadata
        assert s["metadata"] == {"custom_key": "custom_val"}

    def test_ns_to_ms_falsy_input(self):
        """_ns_to_ms returns None for falsy/invalid values."""
        assert _ns_to_ms(None) is None
        assert _ns_to_ms(0) is None
        assert _ns_to_ms("") is None

    def test_ns_to_ms_invalid_type(self):
        """_ns_to_ms returns None for non-numeric strings."""
        assert _ns_to_ms("not-a-number") is None
        assert _ns_to_ms([]) is None

    def test_resource_attr_key_not_found(self):
        """_get_resource_attr returns default when key is missing."""
        resource = {"attributes": [
            {"key": "other.key", "value": {"stringValue": "val"}}
        ]}
        result = _get_resource_attr(resource, "service.name", default="fallback")
        assert result == "fallback"

    def test_resource_attr_empty_attributes(self):
        """_get_resource_attr returns default when attributes list is empty."""
        resource = {"attributes": []}
        result = _get_resource_attr(resource, "service.name", default="mydefault")
        assert result == "mydefault"

    def test_span_with_empty_trace_id_skipped(self):
        """Span with empty traceId is silently skipped."""
        body = {
            "resourceSpans": [{
                "resource": {"attributes": [
                    {"key": "service.name", "value": {"stringValue": "svc"}}
                ]},
                "scopeSpans": [{"spans": [
                    {
                        "traceId": "",  # empty → skip
                        "spanId": "sp-bad",
                        "parentSpanId": "",
                        "name": "bad-span",
                        "kind": 1,
                        "startTimeUnixNano": "1000000000000",
                        "endTimeUnixNano": "2000000000000",
                        "attributes": [],
                        "status": {"code": 1},
                    }
                ]}],
            }]
        }
        groups = map_otlp_request(body)
        assert groups == []

    def test_non_string_input_output_stringified(self):
        """Non-string input/output attributes are converted to str."""
        attrs = [
            {"key": "input", "value": {"intValue": 42}},
            {"key": "output", "value": {"boolValue": True}},
        ]
        body = _make_otlp_body(extra_attrs=attrs)
        _, _, spans = map_otlp_request(body)[0]
        s = spans[0]
        assert s["input"] == "42"
        assert s["output"] == "True"


# ── Integration tests — POST /api/otel/v1/traces ─────────────────────────────


class TestOtelEndpoint:
    def test_ingest_otel_single_trace(self, client, auth_headers):
        """Valid OTLP body creates trace, returns traces_received=1."""
        body = _make_otlp_body(trace_id="otel-trace-1", span_id="otel-span-1")
        resp = client.post("/api/otel/v1/traces", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["traces_received"] == 1

        # Trace visible in listing
        listing = client.get("/api/traces", headers=auth_headers).json()
        ids = [t["id"] for t in listing["traces"]]
        assert "otel-trace-1" in ids

    def test_ingest_otel_empty_body(self, client, auth_headers):
        """Empty body is valid JSON, returns traces_received=0."""
        resp = client.post("/api/otel/v1/traces", json={}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "traces_received": 0}

    def test_ingest_otel_idempotent_second_call(self, client, auth_headers):
        """Same traceId sent twice: spans upserted, not duplicated."""
        body = _make_otlp_body(trace_id="otel-idem-1", span_id="otel-span-x")

        client.post("/api/otel/v1/traces", json=body, headers=auth_headers)
        client.post("/api/otel/v1/traces", json=body, headers=auth_headers)  # same spanId

        detail = client.get("/api/traces/otel-idem-1", headers=auth_headers).json()
        # span_count must remain 1 (upsert guard in add_spans_to_trace)
        assert detail["trace"]["span_count"] == 1

    def test_ingest_otel_multiple_resource_spans(self, client, auth_headers):
        """Two resourceSpans → two distinct traces, traces_received=2."""
        body = {
            "resourceSpans": [
                {
                    "resource": {"attributes": [
                        {"key": "service.name", "value": {"stringValue": "svc-a"}}
                    ]},
                    "scopeSpans": [{"spans": [{
                        "traceId": "multi-trace-1", "spanId": "sp-a1",
                        "parentSpanId": "", "name": "op-a", "kind": 1,
                        "startTimeUnixNano": "1000000000000", "endTimeUnixNano": "2000000000000",
                        "attributes": [], "status": {"code": 1},
                    }]}],
                },
                {
                    "resource": {"attributes": [
                        {"key": "service.name", "value": {"stringValue": "svc-b"}}
                    ]},
                    "scopeSpans": [{"spans": [{
                        "traceId": "multi-trace-2", "spanId": "sp-b1",
                        "parentSpanId": "", "name": "op-b", "kind": 3,
                        "startTimeUnixNano": "1000000000000", "endTimeUnixNano": "2000000000000",
                        "attributes": [], "status": {"code": 1},
                    }]}],
                },
            ]
        }
        resp = client.post("/api/otel/v1/traces", json=body, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["traces_received"] == 2

        listing = client.get("/api/traces", headers=auth_headers).json()
        ids = [t["id"] for t in listing["traces"]]
        assert "multi-trace-1" in ids
        assert "multi-trace-2" in ids
