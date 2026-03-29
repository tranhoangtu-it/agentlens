"""AgentLens SDK — trace AI agents visually."""
__version__ = "0.2.0"

from .tracer import Tracer, SpanExporter, SpanProcessor

_tracer = Tracer()

# Public API
trace = _tracer.trace
span = _tracer.span
configure = _tracer.configure
current_trace = _tracer.current_trace
add_exporter = _tracer.add_exporter
add_processor = _tracer.add_processor
log = _tracer.log
