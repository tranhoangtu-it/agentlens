"""OpenTelemetry-compatible span exporter for AgentLens.

Exports AgentLens SpanData objects as OpenTelemetry spans alongside the normal
AgentLens HTTP transport. Requires ``opentelemetry-api`` and ``opentelemetry-sdk``.

Install::

    pip install agentlens-observe[otel]

Usage::

    import agentlens
    from agentlens.exporters import AgentLensOTelExporter

    exporter = AgentLensOTelExporter(service_name="my-agent")
    agentlens.add_exporter(exporter)

    # Spans now flow to both AgentLens AND your OTel backend (Jaeger, Zipkin, etc.)
    agentlens.configure(server_url="http://localhost:3000")

OTel backend configuration is handled via standard OTel environment variables or
by passing a pre-configured TracerProvider::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    exporter = AgentLensOTelExporter(service_name="my-agent", provider=provider)
"""
import logging
from typing import Optional

logger = logging.getLogger("agentlens.exporters.otel")

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import NonRecordingSpan, SpanContext as OtelSpanContext, TraceFlags
except ImportError:
    raise ImportError(
        "opentelemetry-api and opentelemetry-sdk are required: "
        "pip install agentlens-observe[otel]"
    )

# Lazy import — only needed when AgentLens internal types are referenced
from agentlens.tracer import SpanData


class AgentLensOTelExporter:
    """Export AgentLens spans as OpenTelemetry spans.

    Acts as a bridge: when a span finishes in AgentLens, this exporter creates
    a matching OTel span with all relevant attributes set, then ends it
    immediately. The OTel SDK forwards it to whichever backends are configured
    on the TracerProvider (Jaeger, Zipkin, OTLP, stdout, etc.).

    Args:
        service_name: Logical service name shown in OTel backends.
        provider: Optional pre-configured ``TracerProvider``. When omitted the
                  globally-registered OTel provider is used (``get_tracer_provider()``).
    """

    def __init__(
        self,
        service_name: str = "agentlens",
        provider: Optional[TracerProvider] = None,
    ) -> None:
        self.service_name = service_name
        if provider is not None:
            self._tracer = provider.get_tracer(service_name)
        else:
            self._tracer = otel_trace.get_tracer(service_name)

    # ------------------------------------------------------------------
    # SpanExporter protocol
    # ------------------------------------------------------------------

    def export_span(self, span_data: SpanData) -> None:
        """Convert a completed AgentLens SpanData into an OTel span and export it."""
        try:
            self._do_export(span_data)
        except Exception as exc:
            logger.debug("OTel exporter failed (non-fatal): %s", exc)

    def shutdown(self) -> None:
        """No-op — the TracerProvider lifecycle is managed externally."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_export(self, span: SpanData) -> None:
        start_ns = span.start_ms * 1_000_000  # ms -> nanoseconds

        # Build a deterministic OTel context from the AgentLens span_id so the
        # spans link correctly in the OTel backend.
        trace_id_int = _hex_to_int(span.span_id.replace("-", ""), 32)
        span_id_int = _hex_to_int(span.span_id.replace("-", ""), 16)

        otel_ctx = OtelSpanContext(
            trace_id=trace_id_int,
            span_id=span_id_int,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

        # If there is a parent, link to it via a non-recording parent context
        parent_ctx = None
        if span.parent_id:
            parent_span_id_int = _hex_to_int(span.parent_id.replace("-", ""), 16)
            parent_otel_ctx = OtelSpanContext(
                trace_id=trace_id_int,
                span_id=parent_span_id_int,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
            parent_ctx = otel_trace.set_span_in_context(
                NonRecordingSpan(parent_otel_ctx)
            )

        with self._tracer.start_as_current_span(
            span.name,
            context=parent_ctx,
            start_time=start_ns,
        ) as otel_span:
            # --- Core AgentLens attributes ---
            otel_span.set_attribute("agentlens.span_id", span.span_id)
            otel_span.set_attribute("agentlens.type", span.type)

            if span.input:
                otel_span.set_attribute("agentlens.input", span.input[:512])
            if span.output:
                otel_span.set_attribute("agentlens.output", span.output[:512])

            # --- Cost attributes ---
            if span.cost:
                cost = span.cost
                otel_span.set_attribute("agentlens.cost.model", cost.get("model", ""))
                otel_span.set_attribute(
                    "agentlens.cost.input_tokens", cost.get("input_tokens", 0)
                )
                otel_span.set_attribute(
                    "agentlens.cost.output_tokens", cost.get("output_tokens", 0)
                )
                otel_span.set_attribute(
                    "agentlens.cost.usd", float(cost.get("usd") or 0)
                )
                # Semantic conventions: gen_ai.*
                otel_span.set_attribute("gen_ai.system", cost.get("model", ""))
                otel_span.set_attribute(
                    "gen_ai.usage.prompt_tokens", cost.get("input_tokens", 0)
                )
                otel_span.set_attribute(
                    "gen_ai.usage.completion_tokens", cost.get("output_tokens", 0)
                )

            # --- Metadata / logs as OTel events ---
            if span.metadata:
                logs = span.metadata.pop("logs", None)
                if logs:
                    for entry in logs:
                        ts_ns = entry.get("ts_ms", span.start_ms) * 1_000_000
                        attrs = {k: str(v) for k, v in entry.items() if k != "ts_ms"}
                        otel_span.add_event("agentlens.log", attrs, timestamp=ts_ns)
                # Remaining flat metadata
                for k, v in span.metadata.items():
                    otel_span.set_attribute(f"agentlens.meta.{k}", str(v)[:256])

            # OTel span end time is set by the context manager using
            # ``end_time`` kwarg — patch here via private attribute access
            # because the public API doesn't expose it after start.
            end_ns = (span.end_ms or span.start_ms) * 1_000_000
            # Use end() with explicit timestamp if the span supports it
            try:
                otel_span.end(end_time=end_ns)
            except TypeError:
                pass  # Some implementations don't accept end_time


def _hex_to_int(hex_str: str, bits: int) -> int:
    """Convert a hex string to an integer, masked to `bits` bits."""
    # Pad or truncate to desired length (bits / 4 chars)
    chars = bits // 4
    padded = hex_str.ljust(chars, "0")[:chars]
    try:
        return int(padded, 16)
    except ValueError:
        return 0
