"""Bounded asynchronous in-process event bus."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from itertools import count
from typing import cast
from uuid import UUID

from rci.events.base import Event, EventBusNotRunning, EventPriority, EventQueueFull
from rci.events.handlers import EventHandler, HandlerFailure, Subscription

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EventBusStats:
    published: int
    delivered: int
    handler_failures: int
    rejected_full: int
    queue_depth: int
    subscriptions: int


@dataclass(frozen=True, slots=True)
class _RegisteredHandler:
    subscription_id: UUID
    handler: EventHandler


class EventBus:
    """Priority-aware bounded pub/sub bus with handler-failure isolation.

    `publish()` applies backpressure when the queue is full. `publish_nowait()`
    instead raises `EventQueueFull`. Handler failures are recorded and isolated;
    one failing subscriber cannot prevent later subscribers from receiving an event.
    """

    def __init__(
        self,
        *,
        queue_size: int = 256,
        worker_count: int = 1,
        failure_history_size: int = 100,
    ) -> None:
        if queue_size <= 0:
            raise ValueError("queue_size must be positive")
        if worker_count <= 0:
            raise ValueError("worker_count must be positive")
        if failure_history_size <= 0:
            raise ValueError("failure_history_size must be positive")

        self._queue: asyncio.PriorityQueue[tuple[int, int, Event]] = asyncio.PriorityQueue(
            maxsize=queue_size
        )
        self._worker_count = worker_count
        self._handlers: dict[type[Event], list[_RegisteredHandler]] = defaultdict(list)
        self._workers: list[asyncio.Task[None]] = []
        self._sequence = count()
        self._running = False
        self._published = 0
        self._delivered = 0
        self._handler_failures = 0
        self._rejected_full = 0
        self._failures: deque[HandlerFailure] = deque(maxlen=failure_history_size)

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start dispatcher workers; idempotent."""
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(index), name=f"rci-event-bus-{index}")
            for index in range(self._worker_count)
        ]

    async def stop(self, *, drain: bool = True) -> None:
        """Stop workers, optionally delivering all events accepted before stop."""
        if not self._running:
            return
        if drain:
            await self._queue.join()

        self._running = False
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    def subscribe[E: Event](
        self,
        event_type: type[E],
        handler: Callable[[E], Awaitable[None]],
    ) -> Subscription:
        """Subscribe an async handler to an event class or any of its subclasses."""
        subscription = Subscription.create(cast(type[Event], event_type))
        registered = _RegisteredHandler(
            subscription_id=subscription.subscription_id,
            handler=cast(EventHandler, handler),
        )
        self._handlers[cast(type[Event], event_type)].append(registered)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> bool:
        """Remove one subscription, returning whether it existed."""
        handlers = self._handlers.get(subscription.event_type)
        if not handlers:
            return False

        original_size = len(handlers)
        handlers[:] = [
            registered
            for registered in handlers
            if registered.subscription_id != subscription.subscription_id
        ]
        if not handlers:
            self._handlers.pop(subscription.event_type, None)
        return len(handlers) != original_size

    async def publish(
        self,
        event: Event,
        *,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """Publish with bounded backpressure."""
        self._ensure_running()
        await self._queue.put((int(priority), next(self._sequence), event))
        self._published += 1

    def publish_nowait(
        self,
        event: Event,
        *,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """Publish without blocking, raising when bounded capacity is full."""
        self._ensure_running()
        try:
            self._queue.put_nowait((int(priority), next(self._sequence), event))
        except asyncio.QueueFull as exc:
            self._rejected_full += 1
            raise EventQueueFull("event queue capacity exhausted") from exc
        self._published += 1

    async def join(self) -> None:
        """Wait until every accepted event has been processed by a worker."""
        await self._queue.join()

    def stats(self) -> EventBusStats:
        return EventBusStats(
            published=self._published,
            delivered=self._delivered,
            handler_failures=self._handler_failures,
            rejected_full=self._rejected_full,
            queue_depth=self._queue.qsize(),
            subscriptions=sum(len(handlers) for handlers in self._handlers.values()),
        )

    def recent_failures(self) -> tuple[HandlerFailure, ...]:
        return tuple(self._failures)

    def _ensure_running(self) -> None:
        if not self._running:
            raise EventBusNotRunning("event bus must be started before publishing")

    async def _worker(self, worker_index: int) -> None:
        del worker_index
        try:
            while True:
                _priority, _sequence, event = await self._queue.get()
                try:
                    await self._dispatch(event)
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            raise

    async def _dispatch(self, event: Event) -> None:
        matched: list[_RegisteredHandler] = []
        for subscribed_type, handlers in tuple(self._handlers.items()):
            if isinstance(event, subscribed_type):
                matched.extend(tuple(handlers))

        for registered in matched:
            try:
                await registered.handler(event)
                self._delivered += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # handler isolation is intentional at this boundary
                self._record_handler_failure(event, registered, exc)

    def _record_handler_failure(
        self,
        event: Event,
        registered: _RegisteredHandler,
        exc: Exception,
    ) -> None:
        self._handler_failures += 1
        handler_name = getattr(registered.handler, "__qualname__", repr(registered.handler))
        failure = HandlerFailure(
            event_id=event.event_id,
            event_type=event.event_type,
            subscription_id=registered.subscription_id,
            handler_name=handler_name,
            error_type=type(exc).__name__,
            message=str(exc),
        )
        self._failures.append(failure)
        logger.exception(
            "event handler failed: event_type=%s subscription_id=%s handler=%s",
            event.event_type,
            registered.subscription_id,
            handler_name,
        )
