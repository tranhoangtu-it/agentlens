"""Tests for SpanProcessor plugin hooks."""

import agentlens
from agentlens.tracer import _processors


class RecordingProcessor:
    """Test processor that records on_start/on_end calls."""

    def __init__(self):
        self.started: list = []
        self.ended: list = []

    def on_start(self, span):
        self.started.append(span.name)

    def on_end(self, span):
        self.ended.append(span.name)


class FailingProcessor:
    """Processor that raises — should not break tracing."""

    def on_start(self, span):
        raise RuntimeError("on_start boom")

    def on_end(self, span):
        raise RuntimeError("on_end boom")


def _cleanup():
    _processors.clear()


def test_processor_on_start_and_end():
    _cleanup()
    proc = RecordingProcessor()
    agentlens.add_processor(proc)

    @agentlens.trace
    def my_agent(x):
        with agentlens.span("tool1"):
            pass
        return x

    my_agent("input")
    assert "my_agent" in proc.started
    assert "tool1" in proc.started
    assert "my_agent" in proc.ended
    assert "tool1" in proc.ended
    _cleanup()


def test_processor_error_does_not_break_trace():
    _cleanup()
    agentlens.add_processor(FailingProcessor())

    @agentlens.trace
    def agent_with_bad_processor(x):
        with agentlens.span("work"):
            pass
        return "ok"

    result = agent_with_bad_processor("test")
    assert result == "ok"  # trace completes despite processor errors
    _cleanup()


def test_multiple_processors():
    _cleanup()
    p1 = RecordingProcessor()
    p2 = RecordingProcessor()
    agentlens.add_processor(p1)
    agentlens.add_processor(p2)

    @agentlens.trace
    def multi_agent(x):
        return x

    multi_agent("go")
    assert len(p1.started) == 1
    assert len(p2.started) == 1
    _cleanup()
