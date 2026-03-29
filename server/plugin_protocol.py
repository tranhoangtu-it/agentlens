"""Protocol definition for server-side plugins."""

from typing import Protocol, runtime_checkable

from fastapi import FastAPI


@runtime_checkable
class ServerPlugin(Protocol):
    """Protocol for AgentLens server plugins.

    Plugins are auto-discovered from the server/plugins/ directory.
    Each plugin module must expose a module-level `plugin` instance.
    """

    name: str

    def on_trace_created(self, trace_id: str, agent_name: str, span_count: int) -> None:
        """Called after a new trace is ingested."""
        ...

    def on_trace_completed(self, trace_id: str, agent_name: str) -> None:
        """Called when a trace status becomes 'completed'."""
        ...

    def register_routes(self, app: FastAPI) -> None:
        """Register custom API routes. Called once at startup."""
        ...
