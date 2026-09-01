import asyncio
from typing import Literal

import pytest

from rci.events.base import Event, EventBusNotRunning, EventPriority, EventQueueFull
from rci.events.bus import EventBus


class NamedEvent(Event):
    event_type: Literal["test.named"] = "test.named"
    name: str


@pytest.mark.asyncio
async def test_publish_requires_started_bus() -> None:
    bus = EventBus()
    with pytest.raises(EventBusNotRunning):
        await bus.publish(NamedEvent(source="test", name="one"))


@pytest.mark.asyncio
async def test_subscriber_receives_event() -> None:
    bus = EventBus()
    received: list[str] = []

    async def handler(event: NamedEvent) -> None:
        received.append(event.name)

    bus.subscribe(NamedEvent, handler)
    await bus.start()
    await bus.publish(NamedEvent(source="test", name="one"))
    await bus.join()
    await bus.stop()

    assert received == ["one"]
    assert bus.stats().published == 1
    assert bus.stats().delivered == 1


@pytest.mark.asyncio
async def test_base_event_subscription_receives_subclasses() -> None:
    bus = EventBus()
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.event_type)

    bus.subscribe(Event, handler)
    await bus.start()
    await bus.publish(NamedEvent(source="test", name="one"))
    await bus.join()
    await bus.stop()

    assert received == ["test.named"]


@pytest.mark.asyncio
async def test_handler_failure_is_isolated() -> None:
    bus = EventBus()
    received: list[str] = []

    async def failing_handler(event: NamedEvent) -> None:
        del event
        raise RuntimeError("boom")

    async def healthy_handler(event: NamedEvent) -> None:
        received.append(event.name)

    bus.subscribe(NamedEvent, failing_handler)
    bus.subscribe(NamedEvent, healthy_handler)
    await bus.start()
    await bus.publish(NamedEvent(source="test", name="survives"))
    await bus.join()
    await bus.stop()

    assert received == ["survives"]
    assert bus.stats().handler_failures == 1
    assert bus.stats().delivered == 1
    assert bus.recent_failures()[0].error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_priority_orders_events_already_waiting_in_queue() -> None:
    bus = EventBus(queue_size=4)
    gate = asyncio.Event()
    processing_started = asyncio.Event()
    received: list[str] = []

    async def handler(event: NamedEvent) -> None:
        if event.name == "gate":
            processing_started.set()
            await gate.wait()
        received.append(event.name)

    bus.subscribe(NamedEvent, handler)
    await bus.start()
    await bus.publish(NamedEvent(source="test", name="gate"))
    await processing_started.wait()
    await bus.publish(
        NamedEvent(source="test", name="low"), priority=EventPriority.LOW
    )
    await bus.publish(
        NamedEvent(source="test", name="critical"), priority=EventPriority.CRITICAL
    )
    gate.set()
    await bus.join()
    await bus.stop()

    assert received == ["gate", "critical", "low"]


@pytest.mark.asyncio
async def test_nonblocking_publish_reports_full_queue() -> None:
    bus = EventBus(queue_size=1)
    gate = asyncio.Event()
    processing_started = asyncio.Event()

    async def blocking_handler(event: NamedEvent) -> None:
        if event.name == "first":
            processing_started.set()
            await gate.wait()

    bus.subscribe(NamedEvent, blocking_handler)
    await bus.start()
    bus.publish_nowait(NamedEvent(source="test", name="first"))
    await processing_started.wait()
    bus.publish_nowait(NamedEvent(source="test", name="queued"))

    with pytest.raises(EventQueueFull):
        bus.publish_nowait(NamedEvent(source="test", name="rejected"))

    gate.set()
    await bus.join()
    await bus.stop()
    assert bus.stats().rejected_full == 1


@pytest.mark.asyncio
async def test_unsubscribe_is_deterministic() -> None:
    bus = EventBus()
    received: list[str] = []

    async def handler(event: NamedEvent) -> None:
        received.append(event.name)

    subscription = bus.subscribe(NamedEvent, handler)
    assert bus.unsubscribe(subscription) is True
    assert bus.unsubscribe(subscription) is False

    await bus.start()
    await bus.publish(NamedEvent(source="test", name="ignored"))
    await bus.join()
    await bus.stop()
    assert received == []
