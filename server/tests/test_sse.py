"""Tests for SSE bus in sse.py."""

import asyncio
import pytest
from sse import SSEBus, bus


@pytest.mark.asyncio
async def test_publish_subscribe_basic():
    """Publish event, subscriber receives it."""
    events = []

    async def subscriber():
        async for event in bus.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

    # Start subscriber task
    sub_task = asyncio.create_task(subscriber())

    # Give subscriber time to set up
    await asyncio.sleep(0.01)

    # Publish event
    bus.publish("test_event", {"data": "test"})

    # Wait for subscriber to receive
    await asyncio.wait_for(sub_task, timeout=1.0)

    assert len(events) == 1
    assert "test_event" in events[0]
    assert "test" in events[0]


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """All subscribers receive same event."""
    events1 = []
    events2 = []

    async def subscriber1():
        async for event in bus.subscribe():
            events1.append(event)
            if len(events1) >= 1:
                break

    async def subscriber2():
        async for event in bus.subscribe():
            events2.append(event)
            if len(events2) >= 1:
                break

    # Start both subscribers
    task1 = asyncio.create_task(subscriber1())
    task2 = asyncio.create_task(subscriber2())

    # Give subscribers time to set up
    await asyncio.sleep(0.01)

    # Publish event
    bus.publish("shared_event", {"shared": "data"})

    # Wait for both subscribers
    await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1.0)

    assert len(events1) == 1
    assert len(events2) == 1
    assert "shared" in events1[0]
    assert "shared" in events2[0]


@pytest.mark.asyncio
async def test_event_format():
    """Published events are properly formatted for SSE."""
    events = []

    async def subscriber():
        async for event in bus.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.01)

    # Publish with event type and data
    bus.publish("trace_created", {"trace_id": "123", "agent_name": "test_agent"})

    await asyncio.wait_for(sub_task, timeout=1.0)

    # Verify SSE format (event: ...\ndata: ...\n\n)
    event_str = events[0]
    assert "event:" in event_str
    assert "data:" in event_str
    assert "trace_created" in event_str or "123" in event_str


# ── User filtering ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_filtered_event_only_reaches_matching_subscriber():
    """Events with user_id only reach subscribers with matching user_id."""
    local_bus = SSEBus()
    user_a_events = []
    user_b_events = []

    async def sub_a():
        async for event in local_bus.subscribe(user_id="user-a"):
            user_a_events.append(event)
            break

    async def sub_b():
        async for event in local_bus.subscribe(user_id="user-b"):
            user_b_events.append(event)
            break

    task_a = asyncio.create_task(sub_a())
    task_b = asyncio.create_task(sub_b())
    await asyncio.sleep(0.01)

    # Publish only to user-a
    local_bus.publish("trace_created", {"id": "t1"}, user_id="user-a")

    await asyncio.wait_for(task_a, timeout=1.0)

    # user-b should not have received the event
    assert len(user_a_events) == 1
    assert len(user_b_events) == 0
    task_b.cancel()
    try:
        await task_b
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_broadcast_reaches_all_subscribers():
    """Publishing with user_id=None (broadcast) reaches all subscribers."""
    local_bus = SSEBus()
    events_1 = []
    events_2 = []

    async def sub1():
        async for event in local_bus.subscribe(user_id="user-1"):
            events_1.append(event)
            break

    async def sub2():
        async for event in local_bus.subscribe(user_id="user-2"):
            events_2.append(event)
            break

    t1 = asyncio.create_task(sub1())
    t2 = asyncio.create_task(sub2())
    await asyncio.sleep(0.01)

    # Broadcast (no user_id filter)
    local_bus.publish("system_event", {"msg": "hello"}, user_id=None)

    await asyncio.wait_for(asyncio.gather(t1, t2), timeout=1.0)
    assert len(events_1) == 1
    assert len(events_2) == 1


@pytest.mark.asyncio
async def test_subscriber_with_none_user_id_receives_all_events():
    """A subscriber with user_id=None receives events targeted at any user."""
    local_bus = SSEBus()
    received = []

    async def sub():
        async for event in local_bus.subscribe(user_id=None):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(sub())
    await asyncio.sleep(0.01)

    local_bus.publish("ev1", {"n": 1}, user_id="user-x")
    local_bus.publish("ev2", {"n": 2}, user_id="user-y")

    await asyncio.wait_for(task, timeout=1.0)
    assert len(received) == 2


# ── Queue full cleanup ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_queue_subscriber_is_removed():
    """Subscriber with full queue is dropped from the bus on next publish."""
    local_bus = SSEBus()

    # Create a queue with maxsize=1 and manually add it as subscriber
    full_q: asyncio.Queue = asyncio.Queue(maxsize=1)
    entry = (full_q, None)
    local_bus._subscribers.append(entry)

    # Fill the queue completely so the next put_nowait raises QueueFull
    full_q.put_nowait({"event": "pre", "data": {}})

    # Confirm subscriber is present
    assert entry in local_bus._subscribers

    # Publishing now should trigger QueueFull and remove the dead subscriber
    local_bus.publish("overflow_event", {"x": 1})

    # Dead subscriber should be removed
    assert entry not in local_bus._subscribers


@pytest.mark.asyncio
async def test_subscriber_cleanup_on_generator_exit():
    """When subscriber generator is cancelled, entry is removed from _subscribers."""
    local_bus = SSEBus()

    received = []

    async def long_running_sub():
        async for event in local_bus.subscribe():
            received.append(event)
            # Don't break — keep listening

    task = asyncio.create_task(long_running_sub())
    await asyncio.sleep(0.01)

    # Subscriber should be registered
    assert len(local_bus._subscribers) == 1

    # Cancel the task — triggers finally block in generator → cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # After generator exits (via finally), subscriber is removed
    assert len(local_bus._subscribers) == 0
