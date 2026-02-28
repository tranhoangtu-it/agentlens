"""In-memory SSE event bus for AgentLens real-time trace streaming."""

import asyncio
import json
from typing import AsyncGenerator, Optional


class SSEBus:
    """Broadcast events to subscribers with per-user filtering."""

    def __init__(self):
        # List of (queue, user_id) tuples
        self._subscribers: list[tuple[asyncio.Queue, Optional[str]]] = []

    def publish(self, event_type: str, data: dict, user_id: Optional[str] = None) -> None:
        """Push event to matching subscriber queues. user_id=None broadcasts to all."""
        payload = {"event": event_type, "data": data}
        dead = []
        for q, sub_uid in self._subscribers:
            # Send if: no user filter on event, or subscriber matches event user
            if user_id is None or sub_uid is None or sub_uid == user_id:
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    dead.append((q, sub_uid))
        for entry in dead:
            self._subscribers.remove(entry)

    async def subscribe(self, user_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings for events matching user_id."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        entry = (q, user_id)
        self._subscribers.append(entry)
        try:
            while True:
                payload = await q.get()
                event = payload["event"]
                data = json.dumps(payload["data"])
                yield f"event: {event}\ndata: {data}\n\n"
        finally:
            if entry in self._subscribers:
                self._subscribers.remove(entry)


# Module-level singleton
bus = SSEBus()
